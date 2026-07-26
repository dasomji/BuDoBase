from dataclasses import dataclass
from copy import deepcopy
from typing import Mapping

from django.db import transaction
from django.db.models import F, Max
from django.core.exceptions import ValidationError

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
from budo_app.happy_cleaning_station_matching import station_names_are_similar
from budo_app.happy_cleaning_station_documents import (
    count_tasks,
    project_tasks,
    validate_station_document,
    validate_structural_edit_document,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
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
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        errors["max_kids"] = ["A non-negative integer is required."]
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
    todos = project_tasks(station.content_document)
    assigned_count = station.assignments.count()
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
        "assigned_count": assigned_count,
        "overbooked_count": max(assigned_count - station.max_kids, 0),
        "document": station.content_document,
        "task_item_count": len(todos),
        "todos": todos,
        "responsible": (
            {
                "id": station.responsible_profile.id,
                "name": station.responsible_profile.rufname,
            }
            if station.responsible_profile else None
        ),
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
    todo = next(
        (todo for todo in project_tasks(station.content_document)
         if todo["id"] == todo_id),
        None,
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


def create_station(context, event_id, expected_revision, fields, document):
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
        try:
            station.content_document = _save_structural_document(station, document)
        except ValidationError as error:
            raise CommandError(
                "validation_error",
                errors={"document": error.messages},
            ) from error
        station.save(update_fields=["content_document"])
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


def _task_text_from_document_node(task):
    return "".join(
        child["text"]
        for child in task["content"][0].get("content", [])
    )


TASK_ID_STATION_MULTIPLIER = 1_000_000


def _next_station_task_identity(station):
    """Allocate a JS-safe identity in a station-owned integer namespace."""
    base = station.id * TASK_ID_STATION_MULTIPLIER
    return max(
        (
            task["id"] for task in project_tasks(station.content_document)
            if base <= task["id"] < base + TASK_ID_STATION_MULTIPLIER
        ),
        default=base,
    ) + 1


def _save_structural_document(station, submitted):
    validate_structural_edit_document(submitted)
    current = {todo["id"]: todo for todo in project_tasks(station.content_document)}
    submitted_ids = {
        task["attrs"]["id"]
        for block in submitted["content"]
        if block["type"] == "taskList"
        for task in block["content"]
        if task["attrs"]["id"] is not None
    }
    if not submitted_ids.issubset(current):
        raise ValidationError("A task identity does not belong to this station.")
    document = deepcopy(submitted)
    identity = _next_station_task_identity(station)
    for block in document["content"]:
        if block["type"] != "taskList":
            continue
        for task in block["content"]:
            task_identity = task["attrs"]["id"]
            text = _task_text_from_document_node(task)
            if task_identity is None:
                attrs = {"id": identity, "checked": False, "version": 1}
                identity += 1
            else:
                todo = current[task_identity]
                attrs = {
                    "id": task_identity,
                    "checked": todo["checked"],
                    "version": todo["version"] + (
                        text != todo["text"]
                    ),
                }
            task["attrs"] = attrs
    validate_station_document(document)
    return document


def update_station(
    context,
    event_id,
    station_id,
    expected_version,
    fields,
    document=None,
    overbooking_confirmation=None,
):
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
        assigned_count = station.assignments.count()
        proposed_overbooking = max(assigned_count - fields["max_kids"], 0)
        if proposed_overbooking:
            expected_confirmation = {
                "capacity": fields["max_kids"],
                "assigned_count": assigned_count,
                "station_version": station.version,
            }
            if overbooking_confirmation != expected_confirmation:
                raise CommandError(
                    "overbooking_confirmation_required",
                    status=409,
                    extra={
                        "confirmation": {
                            **expected_confirmation,
                            "overbooked_count": proposed_overbooking,
                        },
                    },
                )
        old_capacity = station.max_kids
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
        if document is not None:
            try:
                station.content_document = _save_structural_document(station, document)
            except ValidationError as error:
                raise CommandError(
                    "validation_error",
                    errors={"document": error.messages},
                ) from error
        station.name = fields["name"]
        station.max_kids = fields["max_kids"]
        station.meeting_point = fields["meeting_point"]
        station.wishes = fields["wishes"]
        station.responsible_profile = responsible
        station.version += 1
        station.save(update_fields=[
            "name", "max_kids", "meeting_point", "wishes",
            "responsible_profile", "content_document", "version",
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
                "old_capacity": old_capacity,
                "new_capacity": station.max_kids,
                "overbooked_count": proposed_overbooking,
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


def _copy_source_document(document, first_identity=1):
    copied = deepcopy(document)
    identity = first_identity
    for node in copied["content"]:
        if node["type"] != "taskList":
            continue
        for task in node["content"]:
            task["attrs"] = {
                "id": identity,
                "checked": False,
                "version": 1,
            }
            identity += 1
    validate_station_document(copied)
    return copied


def _copied_document(source_station, target_station):
    first_identity = _next_station_task_identity(target_station)
    return _copy_source_document(
        source_station.content_document, first_identity,
    )


def _copy_responsible(source_station, source, target):
    if source.turnus_id != target.turnus_id:
        return None
    responsible = source_station.responsible_profile
    return responsible


def _create_station_copy(source_station, source, target, position):
    station = HappyCleaningStation.objects.create(
        happy_cleaning=target,
        name=source_station.name,
        max_kids=source_station.max_kids,
        meeting_point=source_station.meeting_point,
        wishes=source_station.wishes,
        responsible_profile=_copy_responsible(source_station, source, target),
        position=position,
        version=1,
    )
    station.content_document = _copied_document(source_station, station)
    station.save(update_fields=["content_document"])
    return station, count_tasks(station.content_document)["total"]


def _turnus_copy_label(source, source_station):
    return (
        f"Kopiert aus {source_station.name} Happy Cleaning "
        f"{source.display_number} – {source.turnus.turnus_nr}. Turnus "
        f"{source.turnus.turnus_beginn.year}:"
    )


def _validate_resolutions(resolutions, conflicts_by_source, candidates_by_source):
    if not isinstance(resolutions, list):
        raise CommandError(
            "validation_error",
            errors={"resolutions": ["One decision is required per conflicting source."]},
        )
    decisions = {}
    for value in resolutions:
        if not isinstance(value, Mapping):
            raise CommandError("validation_error", errors={"resolutions": ["Malformed decision."]})
        source_id = value.get("source_station_id")
        action = value.get("action")
        target_id = value.get("target_station_id")
        if source_id in decisions or source_id not in conflicts_by_source:
            raise CommandError("validation_error", errors={"resolutions": ["Each conflicting source must occur exactly once."]})
        if action not in {"overwrite", "append", "separate", "skip"}:
            raise CommandError("validation_error", errors={"resolutions": ["Unknown action."]})
        if action in {"overwrite", "append"}:
            if target_id not in candidates_by_source[source_id]:
                raise CommandError("validation_error", errors={"resolutions": ["Choose one matching target station."]})
        elif target_id is not None:
            raise CommandError("validation_error", errors={"resolutions": ["This action does not accept a target station."]})
        decisions[source_id] = (action, target_id)
    if set(decisions) != set(conflicts_by_source):
        raise CommandError(
            "validation_error",
            errors={"resolutions": ["One decision is required per conflicting source."]},
        )
    return decisions


def copy_stations(
    context,
    event_id,
    expected_revision,
    source_event_id,
    station_ids,
    resolutions=None,
):
    return _copy_stations(
        context,
        event_id,
        expected_revision,
        source_event_id=source_event_id,
        station_ids=station_ids,
        resolutions=resolutions,
    )


def copy_single_station(
    context,
    event_id,
    expected_revision,
    source_station_id,
    resolutions=None,
):
    return _copy_stations(
        context,
        event_id,
        expected_revision,
        source_station_id=source_station_id,
        resolutions=resolutions,
    )


def _copy_stations(
    context,
    event_id,
    expected_revision,
    *,
    source_event_id=None,
    station_ids=None,
    resolutions=None,
    source_station_id=None,
):
    action = "happy_cleaning.station.copy"
    with transaction.atomic():
        _locked_turnus(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        target = _locked_event(context, event_id)
        _require_revision(target, expected_revision)
        fixed_source_station = None
        if source_station_id is not None:
            fixed_source_station = (
                HappyCleaningStation.objects.filter(pk=source_station_id)
                .select_related("happy_cleaning__turnus")
                .first()
            )
            if fixed_source_station is None:
                raise CommandError(
                    "not_found",
                    status=404,
                    audit_outcome="forbidden",
                    details={"happy_cleaning_id": target.id},
                )
            source_event_id = fixed_source_station.happy_cleaning_id
        if source_event_id == target.id:
            raise CommandError(
                "invalid_selection",
                errors={"source_event_id": ["Source and target must differ."]},
            )
        source = (
            HappyCleaning.objects.filter(pk=source_event_id)
            .select_related("turnus")
            .first()
        )
        if source is None or (
            source.turnus_id != target.turnus_id
            and source.turnus.turnus_beginn >= target.turnus.turnus_beginn
        ):
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
            .order_by("position", "id")
        )
        selected_by_id = {station.id: station for station in source_stations}
        if fixed_source_station is not None:
            station_ids = [source_station_id]
        if any(station_id not in selected_by_id for station_id in station_ids):
            raise CommandError("invalid_selection", status=400)
        selected = [selected_by_id[station_id] for station_id in station_ids]
        target_stations = list(
            HappyCleaningStation.objects.select_for_update()
            .filter(happy_cleaning=target)
            .order_by("position", "id")
        )
        conflicts = [{
            "source_station_id": source_station.id,
            "source_name": source_station.name,
            "source_task_count": count_tasks(source_station.content_document)["total"],
            "target_station_id": target_station.id,
            "target_name": target_station.name,
            "target_task_count": count_tasks(target_station.content_document)["total"],
            "overwrite_eligible": not target_station.has_ever_had_assignment,
            "overwrite_disabled_reason": (
                None if not target_station.has_ever_had_assignment
                else "Diese Station war bereits einer Einteilung zugeordnet."
            ),
        } for source_station in selected for target_station in target_stations
          if station_names_are_similar(source_station.name, target_station.name)]
        conflicts_by_source = {}
        candidates_by_source = {}
        for conflict in conflicts:
            conflicts_by_source.setdefault(conflict["source_station_id"], []).append(conflict)
            candidates_by_source.setdefault(conflict["source_station_id"], set()).add(
                conflict["target_station_id"]
            )
        if conflicts and resolutions is None:
            return complete_command(context, action, {
                "ok": True,
                "result": "conflicts",
                "target_event_id": target.id,
                "target_revision": target.revision,
                "source_event_id": source.id,
                "station_ids": [station.id for station in selected],
                "conflicts": conflicts,
                "conflict_free_station_ids": [
                    station.id for station in selected
                    if station.id not in conflicts_by_source
                ],
            }), False
        decisions = (
            _validate_resolutions(
                resolutions, conflicts_by_source, candidates_by_source,
            )
            if conflicts else {}
        )
        target_by_id = {station.id: station for station in target_stations}
        for source_id, (resolution, target_id) in decisions.items():
            if (
                resolution == "overwrite"
                and target_by_id[target_id].has_ever_had_assignment
            ):
                raise CommandError(
                    "overwrite_locked",
                    status=409,
                    errors={"resolutions": ["The chosen target has previously been assigned."]},
                )
        next_position = (
            HappyCleaningStation.objects.filter(happy_cleaning=target)
            .aggregate(value=Max("position"))["value"]
            or 0
        )
        copied = []
        affected = []
        result_counts = {
            "copied": 0, "overwritten": 0, "appended": 0, "skipped": 0,
            "todos_created": 0,
        }
        audit_decisions = []
        for source_station in selected:
            resolution, target_station_id = decisions.get(
                source_station.id, ("separate", None),
            )
            if resolution == "skip":
                result_counts["skipped"] += 1
                audit_decisions.append({
                    "source_station_id": source_station.id,
                    "action": "skip",
                    "target_station_id": None,
                })
                continue
            if resolution == "overwrite":
                station = target_by_id[target_station_id]
                station.name = source_station.name
                station.max_kids = source_station.max_kids
                station.meeting_point = source_station.meeting_point
                station.wishes = source_station.wishes
                station.responsible_profile = _copy_responsible(
                    source_station, source, target,
                )
                station.version += 1
                station.content_document = _copied_document(
                    source_station, station,
                )
                station.save(update_fields=[
                    "name", "max_kids", "meeting_point", "wishes",
                    "responsible_profile", "content_document", "version",
                ])
                result_counts["overwritten"] += 1
                result_counts["todos_created"] += count_tasks(
                    station.content_document
                )["total"]
            elif resolution == "append":
                station = target_by_id[target_station_id]
                appended = _copied_document(
                    source_station, station,
                )
                station.content_document = {
                    "type": "doc",
                    "content": [
                        *station.content_document["content"],
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": _turnus_copy_label(source, source_station)}],
                        },
                        *appended["content"],
                    ],
                }
                validate_station_document(station.content_document)
                station.version += 1
                station.save(update_fields=["content_document", "version"])
                result_counts["appended"] += 1
                result_counts["todos_created"] += count_tasks(appended)["total"]
            else:
                next_position += 1
                station, todo_count = _create_station_copy(
                    source_station, source, target, next_position,
                )
                copied.append(station)
                result_counts["copied"] += 1
                result_counts["todos_created"] += todo_count
            affected.append(station)
            audit_decisions.append({
                "source_station_id": source_station.id,
                "action": resolution,
                "target_station_id": target_station_id or station.id,
            })
        if any(value for key, value in result_counts.items() if key != "skipped"):
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
                "source_station_ids": [station.id for station in selected],
                "station_copy_decisions": audit_decisions,
                "station_copy_result_counts": result_counts,
            },
        )
        return complete_command(context, action, {
            "ok": True,
            "result": "resolved" if conflicts else "copied",
            "event": event_projection(target),
            "result_counts": result_counts,
            "copied_stations": [station_projection(item) for item in copied],
            "affected_stations": [
                station_projection(item)
                for item in {item.id: item for item in affected}.values()
            ],
        }), False
