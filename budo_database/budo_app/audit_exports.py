import json
import re
from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth.models import AbstractBaseUser

from budo_app.audit import AuditEventData, actor_label_for_user, record_audit_event
from budo_app.audit_queries import (
    AuditFilters,
    filtered_audit_events,
    selected_audit_turnus,
    serialize_audit_event,
)
from budo_app.models import AuditEvent


class AuditExportTurnusNotFound(LookupError):
    pass


@dataclass(frozen=True)
class AuditExportCommand:
    user: AbstractBaseUser
    filters: AuditFilters
    request_id: str
    client_ip: str | None
    user_agent: str


@dataclass(frozen=True)
class AuditExportResult:
    lines: Iterable[str]
    filename: str


def _json_line(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def _safe_filename_label(label):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "turnus"


def _stream_records(header, queryset):
    yield _json_line(header)
    for event in queryset.iterator(chunk_size=500):
        yield _json_line(serialize_audit_event(event))


def export_audit_events(command):
    turnus = selected_audit_turnus(command.user, command.filters.turnus)
    if turnus is None:
        raise AuditExportTurnusNotFound

    snapshot_id = (
        AuditEvent.objects.filter(turnus_id=turnus.id)
        .order_by("-id")
        .values_list("id", flat=True)
        .first()
    )
    queryset = filtered_audit_events(command.filters, turnus.id)
    if snapshot_id is None:
        queryset = queryset.none()
    else:
        queryset = queryset.filter(id__lte=snapshot_id)
    queryset = queryset.select_related("turnus").order_by("occurred_at", "id")
    result_count = queryset.count()

    record_audit_event(AuditEventData(
        turnus=turnus,
        actor_id=command.user.id,
        actor_label=actor_label_for_user(command.user),
        action="audit.export",
        outcome="success",
        resource_type="audit_log",
        resource_id=str(turnus.id),
        resource_label=f"Audit log {turnus}",
        request_id=command.request_id,
        client_ip=command.client_ip,
        user_agent=command.user_agent,
        details={
            "result_count": result_count,
            "filter_count": sum(
                bool(value) for value in command.filters.as_query_dict().values()
            ),
        },
    ))

    header = {
        "record_type": "header",
        "schema": "budo.audit",
        "version": 1,
        "turnus": {"id": turnus.id, "label": str(turnus)},
    }
    return AuditExportResult(
        lines=_stream_records(header, queryset),
        filename=f"audit-{_safe_filename_label(str(turnus))}.log",
    )
