import math
from urllib.parse import urlencode

from budo_app.audit_queries import (
    AuditFilters,
    audit_turnus_options,
    filtered_audit_events,
    selected_audit_turnus,
    serialize_audit_event,
)
from budo_app.models import AuditEvent


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
    filters = AuditFilters.from_query_params(request.query_params)
    turnus = selected_audit_turnus(request.user, filters.turnus)
    options = audit_turnus_options(request.user)
    if turnus is None:
        filter_values = filters.as_query_dict()
        export_query = urlencode({
            key: value for key, value in filter_values.items() if value
        })
        return {
            "authorized": True,
            "events": [],
            "filters": filter_values,
            "filter_options": {
                "turnuses": options,
                "actions": [], "outcomes": [], "resource_types": [],
            },
            "pagination": {
                "page": 1, "page_size": DEFAULT_PAGE_SIZE, "total": 0,
                "pages": 0, "has_previous": False, "has_next": False,
            },
            "export_url": (
                f"/api/audit-events/export/?{export_query}"
                if export_query else "/api/audit-events/export/"
            ),
        }
    turnus_id = turnus.id
    queryset = filtered_audit_events(filters, turnus_id)
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
    filter_values = filters.as_query_dict()
    if not filter_values["turnus"]:
        filter_values["turnus"] = str(turnus_id)
    export_query = urlencode({
        key: value for key, value in filter_values.items() if value
    })
    return {
        "authorized": True,
        "events": [serialize_audit_event(event) for event in events],
        "filters": filter_values,
        "filter_options": {
            "turnuses": options,
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
