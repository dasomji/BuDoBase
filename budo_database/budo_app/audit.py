import ipaddress
import json
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
    "todo_id": (int,),
    "child_id": (int,),
    "child_name": (str,),
    "previous_station_id": (int, type(None)),
    "new_station_id": (int, type(None)),
    "previous_number": (int, type(None)),
    "new_number": (int, type(None)),
    "expected_version": (int,),
    "current_version": (int,),
    "changed_fields": (list,),
    "result_count": (int,),
    "filter_count": (int,),
}

ACTION_DETAIL_FIELDS = {
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
    "happy_cleaning.assignment.assign": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.move": COMMON_DETAIL_FIELDS,
    "happy_cleaning.assignment.remove": COMMON_DETAIL_FIELDS,
    "audit.export": {
        "result_count": (int,),
        "filter_count": (int,),
    },
}

SENSITIVE_KEY_PARTS = frozenset({
    "body", "cookie", "token", "password", "secret", "health",
    "illness", "drug", "contact", "phone", "email", "money",
    "amount", "allerg", "address", "sozialversicher",
})
MAX_DETAILS_BYTES = 4096
MAX_DETAIL_STRING = 500


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


def _validate_details(action, details):
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
        if isinstance(value, list):
            if len(value) > 50 or not all(
                isinstance(item, str) and len(item) <= 100 for item in value
            ):
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
        "details": _validate_details(data.action, data.details),
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
