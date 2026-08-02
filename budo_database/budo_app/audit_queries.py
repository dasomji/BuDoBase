from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Mapping

from django.db.models import JSONField
from django.db.models.fields.json import KeyTransform
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from budo_app.audit import (
    ACTION_DETAIL_FIELDS,
    AUDIT_VIEW_DETAIL_DETAIL_KEYS,
    AUDIT_VIEW_LIST_DETAIL_KEYS,
)
from budo_app.kid_edit_audit import validate_kid_edit_summary
from budo_app.models import AuditEvent, Profil, Turnus


FILTER_NAMES = (
    "turnus",
    "from",
    "to",
    "actor",
    "action",
    "outcome",
    "resource_type",
    "resource_id",
)


class InvalidAuditListProjection(RuntimeError):
    pass


@dataclass(frozen=True)
class AuditFilters:
    turnus: str = ""
    from_: str = ""
    to: str = ""
    actor: str = ""
    action: str = ""
    outcome: str = ""
    resource_type: str = ""
    resource_id: str = ""

    @classmethod
    def from_query_params(cls, query_params: Mapping[str, object]):
        values = {
            name: str(query_params.get(name, "")).strip()
            for name in FILTER_NAMES
        }
        values["from_"] = values.pop("from")
        return cls(**values)

    def as_query_dict(self):
        values = asdict(self)
        values["from"] = values.pop("from_")
        return values


def _time_boundary(value, *, end):
    parsed = parse_datetime(value) if value else None
    if parsed is not None:
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
    parsed_date = parse_date(value) if value else None
    if parsed_date is None:
        return None
    boundary = datetime.combine(parsed_date, time.min)
    if end:
        boundary += timedelta(days=1)
    return timezone.make_aware(boundary)


def _active_turnus_id(user):
    return (
        Profil.objects.filter(user_id=user.id)
        .values_list("turnus_id", flat=True)
        .first()
    )


def selected_audit_turnus(user, requested_turnus):
    active_turnus_id = _active_turnus_id(user)
    if requested_turnus:
        if not requested_turnus.isdigit():
            return None
        requested_id = int(requested_turnus)
        if not user.is_superuser and requested_id != active_turnus_id:
            return None
        return Turnus.objects.filter(id=requested_id).first()
    if active_turnus_id is None:
        return None
    return Turnus.objects.filter(id=active_turnus_id).first()


def audit_turnus_options(user):
    if user.is_superuser:
        turnuses = Turnus.objects.order_by("turnus_beginn", "id")
    else:
        turnuses = Turnus.objects.filter(id=_active_turnus_id(user))
    return [{"id": turnus.id, "label": str(turnus)} for turnus in turnuses]


def filtered_audit_events(filters, turnus_id):
    queryset = AuditEvent.objects.filter(turnus_id=turnus_id)
    start = _time_boundary(filters.from_, end=False)
    end = _time_boundary(filters.to, end=True)
    if start:
        queryset = queryset.filter(occurred_at__gte=start)
    if end:
        queryset = queryset.filter(occurred_at__lt=end)
    if filters.actor:
        if filters.actor.isdigit():
            queryset = queryset.filter(actor_id=int(filters.actor))
        else:
            queryset = queryset.filter(actor_label__icontains=filters.actor)
    for field in ("action", "outcome", "resource_type", "resource_id"):
        value = getattr(filters, field)
        if value:
            queryset = queryset.filter(**{field: value})
    return queryset


def serialize_audit_event(event):
    timestamp = event.occurred_at.isoformat() if event.occurred_at else None
    if timestamp:
        timestamp = timestamp.replace("+00:00", "Z")
    return {
        "id": event.id,
        "timestamp": timestamp,
        "turnus": {"id": event.turnus_id, "label": str(event.turnus)},
        "actor": {"id": event.actor_id, "label": event.actor_label},
        "action": event.action,
        "outcome": event.outcome,
        "resource": {
            "type": event.resource_type,
            "id": event.resource_id,
            "label": event.resource_label,
        },
        "request_id": event.request_id,
        "client_ip": event.client_ip,
        "user_agent": event.user_agent,
        "details": event.details,
    }


def audit_list_projection(queryset):
    """Return list-safe columns and only the four kid.edit summary fragments."""
    projected_details = Cast("details", output_field=JSONField())
    return queryset.annotate(
        kid_edit_schema=KeyTransform("schema", projected_details),
        kid_edit_version=KeyTransform("version", projected_details),
        kid_edit_result=KeyTransform("result", projected_details),
        kid_edit_changed_paths=KeyTransform(
            "changed_paths", projected_details,
        ),
        audit_view_kind=KeyTransform("view_kind", projected_details),
    ).values(
        "id",
        "occurred_at",
        "turnus_id",
        "actor_id",
        "actor_label",
        "action",
        "outcome",
        "resource_type",
        "resource_id",
        "resource_label",
        "request_id",
        "client_ip",
        "user_agent",
        "kid_edit_schema",
        "kid_edit_version",
        "kid_edit_result",
        "kid_edit_changed_paths",
        "audit_view_kind",
    )


def serialize_audit_list_event(row, *, turnus_label, details_turnus_id=None):
    timestamp = row["occurred_at"].isoformat() if row["occurred_at"] else None
    if timestamp:
        timestamp = timestamp.replace("+00:00", "Z")
    if row["action"] == "kid.edit":
        try:
            summary = validate_kid_edit_summary(
                row["kid_edit_schema"],
                row["kid_edit_version"],
                row["kid_edit_result"],
                row["kid_edit_changed_paths"],
            )
        except Exception as error:
            raise InvalidAuditListProjection(
                "Invalid stored kid.edit summary."
            ) from error
        summary["sensitive"] = True
    elif row["action"] == "audit.view":
        view_kind = row["audit_view_kind"]
        if view_kind == "list":
            allowed_fields = AUDIT_VIEW_LIST_DETAIL_KEYS
        elif view_kind == "detail":
            allowed_fields = AUDIT_VIEW_DETAIL_DETAIL_KEYS
        else:
            raise InvalidAuditListProjection(
                "Invalid stored audit.view discriminator."
            )
        summary = {
            "sensitive": False,
            "available_fields": sorted(allowed_fields),
        }
    else:
        allowed_fields = ACTION_DETAIL_FIELDS.get(row["action"])
        if allowed_fields is None:
            raise InvalidAuditListProjection("Unknown stored audit action.")
        summary = {
            "sensitive": False,
            "available_fields": sorted(allowed_fields),
        }
    details_url = f"/api/audit-events/{row['id']}/"
    if details_turnus_id is not None:
        details_url = f"{details_url}?turnus={details_turnus_id}"
    return {
        "id": row["id"],
        "timestamp": timestamp,
        "turnus": {"id": row["turnus_id"], "label": turnus_label},
        "actor": {"id": row["actor_id"], "label": row["actor_label"]},
        "action": row["action"],
        "outcome": row["outcome"],
        "resource": {
            "type": row["resource_type"],
            "id": row["resource_id"],
            "label": row["resource_label"],
        },
        "request_id": row["request_id"],
        "client_ip": row["client_ip"],
        "user_agent": row["user_agent"],
        "details_summary": summary,
        "details_url": details_url,
    }
