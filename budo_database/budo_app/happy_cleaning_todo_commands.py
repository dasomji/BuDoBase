"""Application services for operative Happy Cleaning todo commands."""

from django.db import transaction
from django.db.models import F

from budo_app.audit import AuditEventData, record_rejected_attempt
from budo_app.happy_cleaning_commands import (
    CommandError,
    audit_success,
    complete_command,
    complete_focused_command,
    event_projection,
    replay_completed_command,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningStation,
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
    with transaction.atomic(savepoint=False):
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
    with transaction.atomic(savepoint=False):
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
        from budo_app.happy_cleaning_station_documents import (
            mutate_task,
            project_tasks,
        )
        todo = next(
            (item for item in project_tasks(station.content_document)
             if item["id"] == todo_id),
            None,
        )
        if todo is None:
            raise CommandError("not_found", status=404, audit_outcome="forbidden")
        if todo["version"] != expected_version:
            raise CommandError(
                "stale",
                status=409,
                current_version=todo["version"],
                audit_outcome="stale",
                details={
                    "happy_cleaning_id": event.id,
                    "station_id": station.id,
                    "todo_id": todo["id"],
                    "expected_version": expected_version,
                    "current_version": todo["version"],
                },
            )
        station.content_document = mutate_task(
            station.content_document,
            todo_id,
            expected_version=expected_version,
            checked=checked,
        )
        station.save(update_fields=("content_document",))
        changed = next(
            item for item in project_tasks(station.content_document)
            if item["id"] == todo_id
        )
        if checked:
            HappyCleaning.objects.filter(pk=event.pk).update(
                has_operational_activity=True,
            )
        HappyCleaning.objects.filter(pk=event.pk).update(
            revision=F("revision") + 1,
        )
        event.refresh_from_db(fields=("revision", "has_operational_activity"))
        audit_success(
            context,
            action=action,
            resource_type="todo",
            resource_id=changed["id"],
            resource_label=changed["text"],
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
                "todo_id": changed["id"],
                "expected_version": expected_version,
                "current_version": changed["version"],
            },
        )
        response = complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "todo": changed,
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
