from dataclasses import dataclass
from typing import Mapping

from django.db import transaction
from django.db.models import F, Max, Q

from budo_app.audit import (
    AuditEventData,
    actor_label_for_user,
    client_ip_from_request,
    record_audit_event,
    record_rejected_attempt,
)
from budo_app.happy_cleaning_assignment_publisher import (
    publish_assignment_invalidation_on_commit,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    HappyCleaningTodo,
    Profil,
    Turnus,
)


class CommandError(Exception):
    def __init__(
        self,
        code,
        *,
        status=400,
        errors=None,
        current_version=None,
        audit_outcome=None,
        details=None,
        extra=None,
    ):
        super().__init__(code)
        self.code = code
        self.status = status
        self.errors = errors
        self.current_version = current_version
        self.audit_outcome = audit_outcome
        self.details = details or {}
        self.extra = extra or {}


@dataclass(frozen=True)
class CommandContext:
    turnus: Turnus
    actor_id: int
    actor_label: str
    request_id: str
    client_ip: str | None
    user_agent: str


def command_context(request, payload):
    if not isinstance(payload, Mapping):
        raise CommandError(
            "validation_error",
            errors={"non_field_errors": ["A JSON object is required."]},
        )
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise CommandError(
            "validation_error",
            errors={"request_id": ["This field is required."]},
        )
    if len(request_id.strip()) > 255:
        raise CommandError(
            "validation_error",
            errors={"request_id": ["Must be at most 255 characters."]},
        )
    profile = (
        Profil.objects.select_related("turnus")
        .filter(user_id=request.user.id, turnus__isnull=False)
        .first()
    )
    if profile is None:
        raise CommandError("not_found", status=404)
    return CommandContext(
        turnus=profile.turnus,
        actor_id=request.user.id,
        actor_label=actor_label_for_user(request.user),
        request_id=request_id.strip(),
        client_ip=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


def required_positive_integer(payload, name):
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CommandError(
            "validation_error",
            errors={name: ["A positive integer is required."]},
        )
    return value


def required_id_list(payload, name):
    value = payload.get(name)
    if not isinstance(value, list) or not value or any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0
        for item in value
    ) or len(set(value)) != len(value):
        raise CommandError(
            "validation_error",
            errors={name: ["A non-empty list of unique positive IDs is required."]},
        )
    return value


def required_text(payload, name, maximum):
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CommandError(
            "validation_error",
            errors={name: ["This field is required."]},
        )
    if len(value.strip()) > maximum:
        raise CommandError(
            "validation_error",
            errors={name: [f"Must be at most {maximum} characters."]},
        )
    return value.strip()


def station_fields(payload):
    errors = {}
    values = {}
    for name, maximum in (("name", 255), ("meeting_point", 500)):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            errors[name] = ["This field is required."]
        elif len(value.strip()) > maximum:
            errors[name] = [f"Must be at most {maximum} characters."]
        else:
            values[name] = value.strip()
    capacity = payload.get("max_kids")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        errors["max_kids"] = ["A positive integer is required."]
    else:
        values["max_kids"] = capacity
    wishes = payload.get("wishes", "")
    if not isinstance(wishes, str):
        errors["wishes"] = ["Must be text."]
    elif len(wishes) > 2000:
        errors["wishes"] = ["Must be at most 2000 characters."]
    else:
        values["wishes"] = wishes.strip()
    responsible_id = payload.get("responsible_profile_id")
    if responsible_id is not None and (
        isinstance(responsible_id, bool)
        or not isinstance(responsible_id, int)
        or responsible_id <= 0
    ):
        errors["responsible_profile_id"] = [
            "Must be a positive profile ID or null.",
        ]
    else:
        values["responsible_profile_id"] = responsible_id
    if errors:
        raise CommandError("validation_error", errors=errors)
    return values


def _locked_turnus(context):
    return Turnus.objects.select_for_update().get(pk=context.turnus.id)


def replay_completed_command(context, action):
    completed = (
        HappyCleaningCommandRequest.objects.select_for_update()
        .filter(
            turnus_id=context.turnus.id,
            actor_id=context.actor_id,
            request_id=context.request_id,
        )
        .first()
    )
    if completed is None:
        return None
    if completed.action != action:
        raise CommandError("request_id_conflict", status=409)
    return {**completed.response, "replayed": True}


def complete_command(context, action, response):
    stored = {**response, "replayed": False}
    HappyCleaningCommandRequest.objects.create(
        turnus=context.turnus,
        actor_id=context.actor_id,
        request_id=context.request_id,
        action=action,
        response=stored,
    )
    return stored


def complete_focused_command(context, action, response):
    stored = complete_command(context, action, response)
    event = response["event"]
    publish_assignment_invalidation_on_commit({
        "kind": "todo",
        "happy_cleaning_id": event["id"],
        "revision": event["revision"],
        "request_id": context.request_id,
    })
    return stored


def audit_success(
    context,
    *,
    action,
    resource_type,
    resource_id,
    resource_label,
    details,
):
    return record_audit_event(AuditEventData(
        turnus=context.turnus,
        actor_id=context.actor_id,
        actor_label=context.actor_label,
        action=action,
        outcome="success",
        resource_type=resource_type,
        resource_id=str(resource_id),
        resource_label=resource_label,
        request_id=context.request_id,
        client_ip=context.client_ip,
        user_agent=context.user_agent,
        details=details,
    ))


def audit_rejection(
    context,
    error,
    *,
    action,
    resource_type,
    resource_id,
    resource_label,
):
    if error.audit_outcome not in {"forbidden", "stale"}:
        return None
    return record_rejected_attempt(AuditEventData(
        turnus=context.turnus,
        actor_id=context.actor_id,
        actor_label=context.actor_label,
        action=action,
        outcome=error.audit_outcome,
        resource_type=resource_type,
        resource_id=str(resource_id),
        resource_label=resource_label,
        request_id=context.request_id,
        client_ip=context.client_ip,
        user_agent=context.user_agent,
        details=error.details,
    ))


def event_projection(event):
    return {
        "id": event.id,
        "display_number": event.display_number,
        "revision": event.revision,
    }


def station_projection(station):
    return {
        "id": station.id,
        "version": station.version,
        "name": station.name,
        "max_kids": station.max_kids,
        "meeting_point": station.meeting_point,
        "wishes": station.wishes,
        "responsible_profile_id": station.responsible_profile_id,
        "position": station.position,
        "has_ever_had_assignment": station.has_ever_had_assignment,
    }


def todo_projection(todo):
    return {
        "id": todo.id,
        "version": todo.version,
        "text": todo.text,
        "position": todo.position,
        "checked": todo.checked,
    }


def _event_not_found(event_id):
    return CommandError(
        "not_found",
        status=404,
        audit_outcome="forbidden",
        details={"happy_cleaning_id": event_id},
    )


def _locked_event(context, event_id):
    event = (
        HappyCleaning.objects.select_for_update()
        .filter(pk=event_id, turnus=context.turnus)
        .first()
    )
    if event is None:
        raise _event_not_found(event_id)
    return event


def _require_version(instance, expected_version, *, detail_id, detail_name):
    if instance.version != expected_version:
        raise CommandError(
            "stale",
            status=409,
            current_version=instance.version,
            audit_outcome="stale",
            details={
                detail_name: detail_id,
                "expected_version": expected_version,
                "current_version": instance.version,
            },
        )


def _require_revision(event, expected_revision):
    if event.revision != expected_revision:
        raise CommandError(
            "stale",
            status=409,
            current_version=event.revision,
            audit_outcome="stale",
            details={
                "happy_cleaning_id": event.id,
                "expected_version": expected_revision,
                "current_version": event.revision,
            },
        )


def _locked_station(event, station_id):
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
    return station


def _locked_todo(station, todo_id):
    todo = (
        HappyCleaningTodo.objects.select_for_update()
        .filter(pk=todo_id, station=station)
        .first()
    )
    if todo is None:
        raise CommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details={"station_id": station.id, "todo_id": todo_id},
        )
    return todo


def _responsible(context, profile_id, *, event_id, station_id=None):
    if profile_id is None:
        return None
    profile = Profil.objects.filter(
        pk=profile_id,
        turnus=context.turnus,
    ).first()
    if profile is None:
        details = {"happy_cleaning_id": event_id}
        if station_id is not None:
            details["station_id"] = station_id
        raise CommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details=details,
        )
    return profile


def _bump_event(event):
    HappyCleaning.objects.filter(pk=event.pk).update(
        revision=F("revision") + 1,
    )
    event.refresh_from_db(fields=["revision", "has_operational_activity"])


def _normalize_stations(event, ordered_ids):
    queryset = HappyCleaningStation.objects.filter(happy_cleaning=event)
    offset = (queryset.aggregate(value=Max("position"))["value"] or 0) + len(ordered_ids) + 1
    queryset.update(position=F("position") + offset)
    for position, station_id in enumerate(ordered_ids, start=1):
        queryset.filter(pk=station_id).update(
            position=position,
            version=F("version") + 1,
        )


def _normalize_todos(station, ordered_ids):
    queryset = HappyCleaningTodo.objects.filter(station=station)
    offset = (queryset.aggregate(value=Max("position"))["value"] or 0) + len(ordered_ids) + 1
    queryset.update(position=F("position") + offset)
    for position, todo_id in enumerate(ordered_ids, start=1):
        queryset.filter(pk=todo_id).update(
            position=position,
            version=F("version") + 1,
        )


def create_event(context):
    action = "happy_cleaning.event.create"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        maximum = (
            HappyCleaning.objects.filter(turnus=context.turnus)
            .aggregate(value=Max("display_number"))["value"]
            or 0
        )
        event = HappyCleaning.objects.create(
            turnus=context.turnus,
            display_number=maximum + 1,
        )
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning",
            resource_id=event.id,
            resource_label=f"Happy Cleaning {event.display_number}",
            details={"happy_cleaning_number": event.display_number},
        )
        response = complete_command(context, action, {
            "ok": True,
            "event": event_projection(event),
        })
        return response, False


def delete_event(context, event_id, expected_revision):
    action = "happy_cleaning.event.delete"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
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
        if event.revision != expected_revision:
            raise CommandError(
                "stale",
                status=409,
                current_version=event.revision,
                audit_outcome="stale",
                details={
                    "happy_cleaning_id": event.id,
                    "expected_version": expected_revision,
                    "current_version": event.revision,
                },
            )
        if event.has_operational_activity:
            raise CommandError("event_locked", status=409)
        deleted_number = event.display_number
        label = f"Happy Cleaning {deleted_number}"
        later_events = list(
            HappyCleaning.objects.select_for_update()
            .filter(
                turnus=context.turnus,
                display_number__gt=deleted_number,
            )
            .order_by("display_number", "id")
        )
        event.delete()
        for later in later_events:
            later.display_number -= 1
            later.revision += 1
            later.save(update_fields=["display_number", "revision"])
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning",
            resource_id=event_id,
            resource_label=label,
            details={"happy_cleaning_number": deleted_number},
        )
        response = complete_command(context, action, {
            "ok": True,
            "deleted_event_id": event_id,
            "events": [
                event_projection(item)
                for item in HappyCleaning.objects.filter(turnus=context.turnus)
            ],
        })
        return response, False


def create_station(context, event_id, expected_revision, fields):
    action = "happy_cleaning.station.create"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        _require_revision(event, expected_revision)
        responsible = _responsible(
            context,
            fields["responsible_profile_id"],
            event_id=event.id,
        )
        position = (
            HappyCleaningStation.objects.filter(happy_cleaning=event)
            .aggregate(value=Max("position"))["value"]
            or 0
        ) + 1
        station = HappyCleaningStation.objects.create(
            happy_cleaning=event,
            name=fields["name"],
            max_kids=fields["max_kids"],
            meeting_point=fields["meeting_point"],
            wishes=fields["wishes"],
            responsible_profile=responsible,
            position=position,
        )
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="station",
            resource_id=station.id,
            resource_label=station.name,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
                "station_name": station.name,
            },
        )
        return complete_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station": station_projection(station),
        }), False


def update_station(context, event_id, station_id, expected_version, fields):
    action = "happy_cleaning.station.update"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        _require_version(
            station,
            expected_version,
            detail_id=station.id,
            detail_name="station_id",
        )
        responsible = _responsible(
            context,
            fields["responsible_profile_id"],
            event_id=event.id,
            station_id=station.id,
        )
        if (
            station.has_ever_had_assignment
            and station.max_kids != fields["max_kids"]
        ):
            raise CommandError("capacity_locked", status=409)
        changed_fields = [
            name for name in (
                "name", "max_kids", "meeting_point", "wishes",
                "responsible_profile_id",
            )
            if getattr(station, name) != (
                responsible.id if name == "responsible_profile_id" and responsible
                else fields[name]
            )
        ]
        station.name = fields["name"]
        station.max_kids = fields["max_kids"]
        station.meeting_point = fields["meeting_point"]
        station.wishes = fields["wishes"]
        station.responsible_profile = responsible
        station.version += 1
        station.save(update_fields=[
            "name", "max_kids", "meeting_point", "wishes",
            "responsible_profile", "version",
        ])
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="station",
            resource_id=station.id,
            resource_label=station.name,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
                "station_name": station.name,
                "changed_fields": changed_fields,
            },
        )
        return complete_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station": station_projection(station),
        }), False


def delete_station(context, event_id, station_id, expected_version):
    action = "happy_cleaning.station.delete"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        _require_version(
            station,
            expected_version,
            detail_id=station.id,
            detail_name="station_id",
        )
        if station.has_ever_had_assignment or station.assignments.exists():
            raise CommandError("station_locked", status=409)
        name = station.name
        station.delete()
        remaining_ids = list(
            HappyCleaningStation.objects.filter(happy_cleaning=event)
            .order_by("position", "id")
            .values_list("id", flat=True)
        )
        _normalize_stations(event, remaining_ids)
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="station",
            resource_id=station_id,
            resource_label=name,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station_id,
                "station_name": name,
            },
        )
        return complete_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "deleted_station_id": station_id,
        }), False


def reorder_stations(context, event_id, expected_revision, station_ids):
    action = "happy_cleaning.station.reorder"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        _require_revision(event, expected_revision)
        current_ids = list(
            HappyCleaningStation.objects.select_for_update()
            .filter(happy_cleaning=event)
            .order_by("position", "id")
            .values_list("id", flat=True)
        )
        if len(current_ids) != len(station_ids) or set(current_ids) != set(station_ids):
            raise CommandError("invalid_order", status=400)
        _normalize_stations(event, station_ids)
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning",
            resource_id=event.id,
            resource_label=f"Happy Cleaning {event.display_number}",
            details={"happy_cleaning_id": event.id},
        )
        return complete_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_ids": station_ids,
        }), False


def create_todo(context, event_id, station_id, expected_version, text):
    action = "happy_cleaning.todo.create"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        _require_version(
            station,
            expected_version,
            detail_id=station.id,
            detail_name="station_id",
        )
        position = (
            HappyCleaningTodo.objects.filter(station=station)
            .aggregate(value=Max("position"))["value"]
            or 0
        ) + 1
        todo = HappyCleaningTodo.objects.create(
            station=station,
            text=text,
            position=position,
        )
        station.version += 1
        station.save(update_fields=["version"])
        _bump_event(event)
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
            },
        )
        return complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "todo": todo_projection(todo),
        }), False


def update_todo(context, event_id, station_id, todo_id, expected_version, text):
    action = "happy_cleaning.todo.update"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        todo = _locked_todo(station, todo_id)
        _require_version(
            todo,
            expected_version,
            detail_id=todo.id,
            detail_name="todo_id",
        )
        todo.text = text
        todo.version += 1
        todo.save(update_fields=["text", "version"])
        station.version += 1
        station.save(update_fields=["version"])
        _bump_event(event)
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
                "changed_fields": ["text"],
            },
        )
        return complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "todo": todo_projection(todo),
        }), False


def reorder_todos(context, event_id, station_id, expected_version, todo_ids):
    action = "happy_cleaning.todo.reorder"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        _require_version(
            station,
            expected_version,
            detail_id=station.id,
            detail_name="station_id",
        )
        current_ids = list(
            HappyCleaningTodo.objects.select_for_update()
            .filter(station=station)
            .order_by("position", "id")
            .values_list("id", flat=True)
        )
        if len(current_ids) != len(todo_ids) or set(current_ids) != set(todo_ids):
            raise CommandError("invalid_order", status=400)
        _normalize_todos(station, todo_ids)
        station.version += 1
        station.save(update_fields=["version"])
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="station",
            resource_id=station.id,
            resource_label=station.name,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
            },
        )
        return complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "todo_ids": todo_ids,
        }), False


def delete_todo(context, event_id, station_id, todo_id, expected_version):
    action = "happy_cleaning.todo.delete"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _locked_event(context, event_id)
        station = _locked_station(event, station_id)
        todo = _locked_todo(station, todo_id)
        _require_version(
            todo,
            expected_version,
            detail_id=todo.id,
            detail_name="todo_id",
        )
        label = todo.text
        todo.delete()
        remaining_ids = list(
            HappyCleaningTodo.objects.filter(station=station)
            .order_by("position", "id")
            .values_list("id", flat=True)
        )
        _normalize_todos(station, remaining_ids)
        station.version += 1
        station.save(update_fields=["version"])
        _bump_event(event)
        audit_success(
            context,
            action=action,
            resource_type="todo",
            resource_id=todo_id,
            resource_label=label,
            details={
                "happy_cleaning_id": event.id,
                "station_id": station.id,
                "todo_id": todo_id,
            },
        )
        return complete_focused_command(context, action, {
            "ok": True,
            "event": event_projection(event),
            "station_version": station.version,
            "deleted_todo_id": todo_id,
        }), False


def _copy_source_event(target):
    return (
        HappyCleaning.objects.filter(
            Q(turnus__turnus_beginn__lt=target.turnus.turnus_beginn)
            | Q(
                turnus=target.turnus,
                display_number__lt=target.display_number,
            )
        )
        .select_related("turnus")
    )


def copy_stations(
    context,
    event_id,
    expected_revision,
    source_event_id,
    *,
    copy_all,
    station_ids,
    duplicate_strategy,
):
    action = "happy_cleaning.station.copy"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        target = _locked_event(context, event_id)
        _require_revision(target, expected_revision)
        source = _copy_source_event(target).filter(pk=source_event_id).first()
        if source is None:
            raise CommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={
                    "happy_cleaning_id": target.id,
                    "source_happy_cleaning_id": source_event_id,
                },
            )
        source_stations = list(
            HappyCleaningStation.objects.filter(happy_cleaning=source)
            .select_related("responsible_profile")
            .prefetch_related("todos")
            .order_by("position", "id")
        )
        if copy_all:
            selected = source_stations
        else:
            selected_by_id = {station.id: station for station in source_stations}
            if station_ids is None or any(
                station_id not in selected_by_id for station_id in station_ids
            ):
                raise CommandError("invalid_selection", status=400)
            selected = [selected_by_id[station_id] for station_id in station_ids]
        existing_names = {
            name.strip().casefold(): name
            for name in HappyCleaningStation.objects.filter(
                happy_cleaning=target,
            ).values_list("name", flat=True)
        }
        duplicates = sorted({
            station.name for station in selected
            if station.name.strip().casefold() in existing_names
        }, key=str.casefold)
        if duplicates and duplicate_strategy not in {"copy", "skip"}:
            raise CommandError(
                "duplicate_names",
                status=409,
                extra={"duplicate_names": duplicates},
            )
        if duplicate_strategy == "skip":
            selected = [
                station for station in selected
                if station.name.strip().casefold() not in existing_names
            ]
        next_position = (
            HappyCleaningStation.objects.filter(happy_cleaning=target)
            .aggregate(value=Max("position"))["value"]
            or 0
        )
        copied = []
        for source_station in selected:
            next_position += 1
            responsible = source_station.responsible_profile
            if responsible and responsible.turnus_id != target.turnus_id:
                responsible = None
            station = HappyCleaningStation.objects.create(
                happy_cleaning=target,
                name=source_station.name,
                max_kids=source_station.max_kids,
                meeting_point=source_station.meeting_point,
                wishes=source_station.wishes,
                responsible_profile=responsible,
                position=next_position,
            )
            HappyCleaningTodo.objects.bulk_create([
                HappyCleaningTodo(
                    station=station,
                    text=todo.text,
                    position=position,
                    checked=False,
                    version=1,
                )
                for position, todo in enumerate(
                    source_station.todos.all(),
                    start=1,
                )
            ])
            copied.append(station)
        _bump_event(target)
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning",
            resource_id=target.id,
            resource_label=f"Happy Cleaning {target.display_number}",
            details={
                "happy_cleaning_id": target.id,
                "source_happy_cleaning_id": source.id,
                "copied_station_count": len(copied),
            },
        )
        return complete_command(context, action, {
            "ok": True,
            "event": event_projection(target),
            "copied_stations": [station_projection(item) for item in copied],
        }), False
