import ipaddress
import json
import re
from dataclasses import dataclass
from typing import Mapping

from django.core.exceptions import ValidationError
from django.db import connection

from budo_app.models import AuditEvent, Turnus


class AuditTransactionError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuditEventData:
    turnus: Turnus
    actor_id: int | None
    actor_label: str
    action: str
    outcome: str
    resource_type: str
    resource_id: str
    resource_label: str
    request_id: str
    client_ip: str | None
    user_agent: str
    details: Mapping[str, object]


OUTCOMES = frozenset({
    "success",
    "forbidden",
    "stale",
    "station_full",
    "duplicate_number",
})

COMMON_DETAIL_FIELDS = {
    "happy_cleaning_id": (int,),
    "happy_cleaning_number": (int,),
    "station_id": (int,),
    "station_name": (str,),
    "source_happy_cleaning_id": (int,),
    "copied_station_count": (int,),
    "source_station_ids": (list,),
    "station_copy_decisions": (list,),
    "station_copy_result_counts": (dict,),
    "todo_id": (int,),
    "child_id": (int,),
    "child_name": (str,),
    "previous_station_id": (int, str, type(None)),
    "new_station_id": (int, str, type(None)),
    "previous_number": (int, type(None)),
    "new_number": (int, type(None)),
    "expected_version": (int,),
    "current_version": (int,),
    "changed_fields": (list,),
    "old_capacity": (int,),
    "new_capacity": (int,),
    "overbooked_count": (int,),
    "result_count": (int,),
    "filter_count": (int,),
}

AUDIT_VIEW_LIST_DETAIL_KEYS = frozenset({
    "view_kind", "result_count", "filter_count", "page", "page_size",
    "snapshot_id", "sensitive_payload_count",
})
AUDIT_VIEW_DETAIL_DETAIL_KEYS = frozenset({
    "view_kind", "result_count", "filter_count", "audit_event_id",
    "snapshot_id", "sensitive_payload_count",
})
AUDIT_EXPORT_DETAIL_KEYS = frozenset({"result_count", "filter_count"})

ACTION_DETAIL_FIELDS = {
    "turnus.selection.switch": {
        "previous_turnus_id": (int, type(None)),
        "selected_turnus_id": (int,),
    },
    "membership.role.change": {
        "previous_role": (str,),
        "new_role": (str,),
        "member_id": (int,),
    },
    "membership.create": {
        "functional_role": (str,),
        "member_id": (int,),
    },
    "happy_cleaning.event.create": COMMON_DETAIL_FIELDS,
    "happy_cleaning.event.update": COMMON_DETAIL_FIELDS,
    "happy_cleaning.event.delete": COMMON_DETAIL_FIELDS,
    "happy_cleaning.station.create": COMMON_DETAIL_FIELDS,
    "happy_cleaning.station.update": COMMON_DETAIL_FIELDS,
    "happy_cleaning.station.reorder": COMMON_DETAIL_FIELDS,
    "happy_cleaning.station.delete": COMMON_DETAIL_FIELDS,
    "happy_cleaning.station.copy": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.create": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.update": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.reorder": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.delete": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.check": COMMON_DETAIL_FIELDS,
    "happy_cleaning.todo.reopen": COMMON_DETAIL_FIELDS,
    "happy_cleaning.child_number.set": COMMON_DETAIL_FIELDS,
    "happy_cleaning.child_number.change": COMMON_DETAIL_FIELDS,
    "happy_cleaning.child_number.batch_assign": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.assign": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.excuse": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.move": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.move_to_excused": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.remove": COMMON_DETAIL_FIELDS,
    "audit.export": {key: (int,) for key in AUDIT_EXPORT_DETAIL_KEYS},
    "audit.view": {
        key: ((str,) if key == "view_kind" else (int,))
        for key in AUDIT_VIEW_LIST_DETAIL_KEYS
    },
}

SENSITIVE_KEY_PARTS = frozenset({
    "body", "cookie", "token", "password", "secret", "health",
    "illness", "drug", "contact", "phone", "email", "money",
    "amount", "allerg", "address", "sozialversicher",
})
MAX_DETAILS_BYTES = 4096
MAX_DETAIL_STRING = 500
MAX_AUDIT_LIST_PAGE_SIZE = 100
MAX_AUDIT_FILTER_COUNT = 8
POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807


def canonical_client_ip(value):
    if value in (None, ""):
        return None
    try:
        return str(ipaddress.ip_address(str(value).strip()))
    except ValueError as error:
        raise ValidationError({"client_ip": "Invalid client IP address."}) from error


def client_ip_from_request(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded.split(",", 1)[0].strip() if forwarded else ""
    return canonical_client_ip(candidate or request.META.get("REMOTE_ADDR"))


def actor_label_for_user(user):
    profile = getattr(user, "profil", None)
    return (getattr(profile, "rufname", "") or user.get_username()).strip()


def _validate_short_text(name, value, maximum, *, required=True):
    if not isinstance(value, str):
        raise ValidationError({name: "Must be text."})
    if required and not value.strip():
        raise ValidationError({name: "Must not be blank."})
    if len(value) > maximum:
        raise ValidationError({name: f"Must be at most {maximum} characters."})


def _contains_sensitive_key(key):
    lowered = key.casefold()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)

def _valid_json_detail(value, *, depth=0):
    if depth > 3:
        return False
    if value is None or isinstance(value, (str, int, bool)):
        return not isinstance(value, str) or len(value) <= MAX_DETAIL_STRING
    if isinstance(value, list):
        return len(value) <= 50 and all(
            _valid_json_detail(item, depth=depth + 1) for item in value
        )
    if isinstance(value, dict):
        return len(value) <= 50 and all(
            isinstance(key, str)
            and not _contains_sensitive_key(key)
            and _valid_json_detail(item, depth=depth + 1)
            for key, item in value.items()
        )
    return False


def _validate_details(action, details):
    if action == "kid.edit":
        from budo_app.kid_edit_audit import validate_kid_edit_details

        return validate_kid_edit_details(details)
    if action == "audit.export":
        if (
            not isinstance(details, Mapping)
            or frozenset(details) != AUDIT_EXPORT_DETAIL_KEYS
            or any(
                not isinstance(details[name], int)
                or isinstance(details[name], bool)
                for name in AUDIT_EXPORT_DETAIL_KEYS
            )
            or details["result_count"] < 0
            or details["result_count"] > POSTGRES_BIGINT_MAX
            or details["filter_count"] < 0
            or details["filter_count"] > MAX_AUDIT_FILTER_COUNT
        ):
            raise ValidationError({"details": "Invalid audit.export schema."})
        validated = dict(details)
        encoded = json.dumps(
            validated, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > MAX_DETAILS_BYTES:
            raise ValidationError({"details": "Details object is too large."})
        return validated
    if action == "audit.view":
        if not isinstance(details, Mapping):
            raise ValidationError({"details": "Must be an action-specific object."})
        view_kind = details.get("view_kind")
        if view_kind == "list":
            expected_keys = AUDIT_VIEW_LIST_DETAIL_KEYS
        elif view_kind == "detail":
            expected_keys = AUDIT_VIEW_DETAIL_DETAIL_KEYS
        else:
            raise ValidationError({"details": "Invalid audit.view schema."})
        if frozenset(details) != expected_keys:
            raise ValidationError({"details": "Invalid audit.view schema."})
        integer_fields = expected_keys - {"view_kind"}
        if any(
            not isinstance(details[name], int) or isinstance(details[name], bool)
            for name in integer_fields
        ):
            raise ValidationError({"details": "Invalid audit.view schema."})
        if view_kind == "list":
            invalid = (
                details["result_count"] < 0
                or details["result_count"] > details["page_size"]
                or details["filter_count"] < 0
                or details["filter_count"] > MAX_AUDIT_FILTER_COUNT
                or details["page"] < 1
                or details["page"] > POSTGRES_BIGINT_MAX
                or details["page_size"] < 1
                or details["page_size"] > MAX_AUDIT_LIST_PAGE_SIZE
                or details["snapshot_id"] < 0
                or details["snapshot_id"] > POSTGRES_BIGINT_MAX
                or details["sensitive_payload_count"] != 0
            )
        else:
            invalid = (
                details["result_count"] != 1
                or details["filter_count"] != 0
                or details["audit_event_id"] < 1
                or details["audit_event_id"] > POSTGRES_BIGINT_MAX
                or details["snapshot_id"] != details["audit_event_id"]
                or details["sensitive_payload_count"] not in {0, 1}
            )
        if invalid:
            raise ValidationError({"details": "Invalid audit.view schema."})
        validated = dict(details)
        encoded = json.dumps(
            validated, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > MAX_DETAILS_BYTES:
            raise ValidationError({"details": "Details object is too large."})
        return validated
    if not isinstance(details, Mapping):
        raise ValidationError({"details": "Must be an action-specific object."})
    schema = ACTION_DETAIL_FIELDS.get(action)
    if schema is None:
        raise ValidationError({"action": "Unknown audit action."})
    validated = {}
    for key, value in details.items():
        if not isinstance(key, str) or _contains_sensitive_key(key):
            raise ValidationError({"details": f"Forbidden detail key: {key}."})
        expected = schema.get(key)
        if expected is None:
            raise ValidationError({"details": f"Unknown detail key: {key}."})
        if not isinstance(value, expected) or (
            isinstance(value, bool) and int in expected and bool not in expected
        ):
            raise ValidationError({"details": f"Invalid value for {key}."})
        if isinstance(value, str) and len(value) > MAX_DETAIL_STRING:
            raise ValidationError({"details": f"Value for {key} is too large."})
        if not _valid_json_detail(value):
            raise ValidationError({"details": f"Invalid value for {key}."})
        validated[key] = value
    encoded = json.dumps(validated, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DETAILS_BYTES:
        raise ValidationError({"details": "Details object is too large."})
    return validated


def _validated_fields(data):
    if not isinstance(data.turnus, Turnus) or data.turnus.pk is None:
        raise ValidationError({"turnus": "A persisted Turnus is required."})
    if data.outcome not in OUTCOMES:
        raise ValidationError({"outcome": "Unknown audit outcome."})
    limits = {
        "actor_label": (data.actor_label, 255),
        "action": (data.action, 100),
        "resource_type": (data.resource_type, 100),
        "resource_id": (data.resource_id, 100),
        "resource_label": (data.resource_label, 255),
        "request_id": (data.request_id, 255),
        "user_agent": (data.user_agent, 1000),
    }
    for name, (value, maximum) in limits.items():
        _validate_short_text(
            name,
            value,
            maximum,
            required=name != "user_agent",
        )
    if data.actor_id is not None and (
        not isinstance(data.actor_id, int) or isinstance(data.actor_id, bool)
        or data.actor_id <= 0
    ):
        raise ValidationError({"actor_id": "Must be a positive integer or null."})
    validated_details = _validate_details(data.action, data.details)
    if data.action == "kid.edit" and (
        data.outcome != "success"
        or data.resource_type != "child"
        or re.fullmatch(r"[1-9]\d*", data.resource_id) is None
        or int(data.resource_id) > 9_223_372_036_854_775_807
    ):
        raise ValidationError({"action": "Invalid kid.edit audit envelope."})
    if data.action == "audit.view":
        if validated_details["view_kind"] == "list":
            invalid_envelope = (
                data.outcome != "success"
                or data.resource_type != "audit_log"
                or data.resource_id != str(data.turnus.pk)
                or data.resource_label != str(data.turnus)
            )
        else:
            event_id = validated_details["audit_event_id"]
            invalid_envelope = (
                data.outcome != "success"
                or data.resource_type != "audit_event"
                or data.resource_id != str(event_id)
                or data.resource_label != f"Audit event {event_id}"
            )
        if invalid_envelope:
            raise ValidationError({"action": "Invalid audit.view audit envelope."})
    if data.action == "audit.export" and (
        data.outcome != "success"
        or data.resource_type != "audit_log"
        or data.resource_id != str(data.turnus.pk)
        or data.resource_label != f"Audit log {data.turnus}"
    ):
        raise ValidationError({"action": "Invalid audit.export audit envelope."})
    return {
        "turnus": data.turnus,
        "actor_id": data.actor_id,
        "actor_label": data.actor_label.strip(),
        "action": data.action,
        "outcome": data.outcome,
        "resource_type": data.resource_type,
        "resource_id": data.resource_id,
        "resource_label": data.resource_label.strip(),
        "request_id": data.request_id.strip(),
        "client_ip": canonical_client_ip(data.client_ip),
        "user_agent": data.user_agent,
        "details": validated_details,
    }


def record_audit_event(data: AuditEventData):
    """Write a validated event in the caller's domain transaction."""
    return AuditEvent.objects._create_validated_event(**_validated_fields(data))


def record_rejected_attempt(data: AuditEventData):
    """Write a selected rejection only after a failed domain transaction ends."""
    if data.outcome == "success":
        raise ValidationError({"outcome": "Rejected attempts cannot be successful."})
    if connection.in_atomic_block or connection.needs_rollback:
        raise AuditTransactionError(
            "Rejected attempts must be recorded after the domain transaction ends."
        )
    return record_audit_event(data)
