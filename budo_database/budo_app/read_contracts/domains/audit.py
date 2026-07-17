import math
from urllib.parse import urlencode
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from budo_app.models import AuditEvent
from budo_app.read_contracts.common import (
    active_turnus_id,
    serialize_utc_datetime,
)


FILTER_NAMES = (
    "from",
    "to",
    "actor",
    "action",
    "outcome",
    "resource_type",
    "resource_id",
)
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _positive_integer(value, default, *, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if result < 1:
        return default
    return min(result, maximum) if maximum else result


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


def audit_filters(request):
    return {
        name: str(request.query_params.get(name, "")).strip()
        for name in FILTER_NAMES
    }


def filtered_audit_events(request, turnus_id):
    filters = audit_filters(request)
    queryset = AuditEvent.objects.filter(turnus_id=turnus_id)
    start = _time_boundary(filters["from"], end=False)
    end = _time_boundary(filters["to"], end=True)
    if start:
        queryset = queryset.filter(occurred_at__gte=start)
    if end:
        queryset = queryset.filter(occurred_at__lt=end)
    actor = filters["actor"]
    if actor:
        if actor.isdigit():
            queryset = queryset.filter(actor_id=int(actor))
        else:
            queryset = queryset.filter(actor_label__icontains=actor)
    for field in ("action", "outcome", "resource_type", "resource_id"):
        if filters[field]:
            queryset = queryset.filter(**{field: filters[field]})
    return queryset, filters


def serialize_audit_event(event):
    return {
        "id": event.id,
        "timestamp": serialize_utc_datetime(event.occurred_at),
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


def _distinct_values(turnus_id, model_field):
    return list(
        AuditEvent.objects.filter(turnus_id=turnus_id)
        .order_by(model_field)
        .values_list(model_field, flat=True)
        .distinct()
    )


def audit_events(request):
    if not request.user.has_perm("budo_app.view_auditevent"):
        return {"authorized": False, "events": []}
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {
            "authorized": True,
            "events": [],
            "filters": audit_filters(request),
            "filter_options": {
                "actions": [], "outcomes": [], "resource_types": [],
            },
            "pagination": {
                "page": 1, "page_size": DEFAULT_PAGE_SIZE, "total": 0,
                "pages": 0, "has_previous": False, "has_next": False,
            },
            "export_url": "/api/audit-events/export/",
        }
    queryset, filters = filtered_audit_events(request, turnus_id)
    queryset = queryset.select_related("turnus").order_by("-occurred_at", "-id")
    page = _positive_integer(request.query_params.get("page"), 1)
    page_size = _positive_integer(
        request.query_params.get("page_size"),
        DEFAULT_PAGE_SIZE,
        maximum=MAX_PAGE_SIZE,
    )
    total = queryset.count()
    pages = math.ceil(total / page_size) if total else 0
    if pages and page > pages:
        page = pages
    start = (page - 1) * page_size
    events = list(queryset[start:start + page_size])
    export_query = urlencode({key: value for key, value in filters.items() if value})
    return {
        "authorized": True,
        "events": [serialize_audit_event(event) for event in events],
        "filters": filters,
        "filter_options": {
            "actions": _distinct_values(turnus_id, "action"),
            "outcomes": _distinct_values(turnus_id, "outcome"),
            "resource_types": _distinct_values(turnus_id, "resource_type"),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        },
        "export_url": (
            f"/api/audit-events/export/?{export_query}"
            if export_query else "/api/audit-events/export/"
        ),
    }


CONTRACTS = {"audit-events": audit_events}
