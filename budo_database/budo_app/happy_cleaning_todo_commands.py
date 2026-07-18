"""Application services for operative Happy Cleaning todo commands."""

from django.db import transaction
from django.db.models import F

from budo_app.audit import AuditEventData, record_rejected_attempt
from budo_app.happy_cleaning_commands import (
    CommandError,
    audit_success,
    complete_command,
    complete_focused_command,
    create_todo,
    event_projection,
    replay_completed_command,
    todo_projection,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningStation,
    HappyCleaningTodo,
    Profil,
    Turnus,
)


def rejection_response(
    context,
    action,
    error,
    *,
    resource_type,
    resource_id,
):
    """Consume a selected rejected request ID and make it replayable."""
    with transaction.atomic():
        Profil.objects.select_for_update().get(user_id=context.actor_id)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        payload = {"ok": False, "code": error.code}
        if error.errors is not None:
            payload["errors"] = error.errors
        if error.current_version is not None:
            payload["current_version"] = error.current_version
        response = complete_command(context, action, payload)
    record_rejected_attempt(AuditEventData(
        turnus=context.turnus,
        actor_id=context.actor_id,
        actor_label=context.actor_label,
        action=action,
        outcome=error.audit_outcome,
        resource_type=resource_type,
        resource_id=str(resource_id),
        resource_label=f"{resource_type.title()} #{resource_id}",
        request_id=context.request_id,
        client_ip=context.client_ip,
        user_agent=context.user_agent,
        details=error.details,
    ))
    return response, False


def add_todo(context, event_id, station_id, expected_version, text):
    """Append an operative todo using the station management invariant."""
    return create_todo(
        context,
        event_id,
        station_id,
        expected_version,
        text,
    )


def _locked_event(context, event_id):
    event = (
        HappyCleaning.objects.select_for_update()
        .filter(pk=event_id, turnus=context.turnus)
        .first()
    )
    if event is None:
        raise CommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details={"happy_cleaning_id": event_id},
        )
    return event


def _locked_todo(event, station_id, todo_id):
    todo = (
        HappyCleaningTodo.objects.select_for_update()
        .select_related("station")
        .filter(
            pk=todo_id,
            station_id=station_id,
            station__happy_cleaning=event,
        )
        .first()
    )
    if todo is None:
        raise CommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details={
                "happy_cleaning_id": event.id,
                "station_id": station_id,
                "todo_id": todo_id,
            },
        )
    return todo


def _set_checked(
    context,
    event_id,
    station_id,
    todo_id,
    expected_version,
    *,
    checked,
):
    action = (
        "happy_cleaning.todo.check"
        if checked
        else "happy_cleaning.todo.reopen"
    )
    with transaction.atomic():
        Turnus.objects.select_for_update().get(pk=context.turnus.id)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        # Locking the station makes the lock order match add/edit/reorder.
        station = (
            HappyCleaningStation.objects.select_for_update()
            .filter(pk=station_id, happy_cleaning=event)
            .first()
        )
        if station is None:
            raise CommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={
                    "happy_cleaning_id": event.id,
                    "station_id": station_id,
                },
            )
        todo = _locked_todo(event, station.id, todo_id)
        if todo.version != expected_version:
            raise CommandError(
                "stale",
                status=409,
                current_version=todo.version,
                audit_outcome="stale",
                details={
                    "happy_cleaning_id": event.id,
                    "station_id": station.id,
                    "todo_id": todo.id,
                    "expected_version": expected_version,
                    "current_version": todo.version,
                },
            )
        todo.checked = checked
        todo.version += 1
        todo.save(update_fields=("checked", "version"))
        HappyCleaning.objects.filter(pk=event.pk).update(
            revision=F("revision") + 1,
        )
        event.refresh_from_db(fields=("revision", "has_operational_activity"))
        audit_success(
            context,
            action=action,
            resource_type="todo",
            resource_id=todo.id,
            resource_label=todo.text,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
                "todo_id": todo.id,
                "expected_version": expected_version,
                "current_version": todo.version,
            },
        )
        response = complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "todo": todo_projection(todo),
        })
        return response, False


def check_todo(context, event_id, station_id, todo_id, expected_version):
    return _set_checked(
        context,
        event_id,
        station_id,
        todo_id,
        expected_version,
        checked=True,
    )


def reopen_todo(context, event_id, station_id, todo_id, expected_version):
    return _set_checked(
        context,
        event_id,
        station_id,
        todo_id,
        expected_version,
        checked=False,
    )
