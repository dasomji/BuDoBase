import math
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError as ApiValidationError

from budo_app.audit_policy import can_view_audit, log_audit_denial
from budo_app.audit_queries import (
    AuditFilters,
    InvalidAuditListProjection,
    audit_list_projection,
    audit_turnus_options,
    filtered_audit_events,
    selected_audit_turnus,
    serialize_audit_list_event,
)
from budo_app.models import AuditEvent


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class AuditListUnavailable(APIException):
    status_code = 503
    default_detail = "Audit list is temporarily unavailable."
    default_code = "audit_list_unavailable"


def _positive_integer(value, default, *, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if result < 1:
        return default
    return min(result, maximum) if maximum else result


def _snapshot_id(value, *, turnus_id):
    current_max = (
        AuditEvent.objects.filter(turnus_id=turnus_id)
        .aggregate(value=Max("id"))["value"]
        or 0
    )
    if value is None or value == "":
        return current_max
    try:
        snapshot_id = int(value)
    except (TypeError, ValueError) as error:
        raise ApiValidationError({"snapshot_id": "Must be a valid snapshot."}) from error
    if snapshot_id < 0 or snapshot_id > current_max:
        raise ApiValidationError({"snapshot_id": "Must be a valid snapshot."})
    return snapshot_id


def _distinct_values(turnus_id, model_field, *, snapshot_id):
    return list(
        AuditEvent.objects.filter(turnus_id=turnus_id, id__lte=snapshot_id)
        .order_by(model_field)
        .values_list(model_field, flat=True)
        .distinct()
    )


def audit_events(request):
    if not can_view_audit(request.user):
        log_audit_denial(
            user=request.user,
            endpoint_kind="list",
            reason_code="forbidden",
        )
        raise PermissionDenied("Audit access denied.")
    filters = AuditFilters.from_query_params(request.query_params)
    turnus = selected_audit_turnus(request.user, filters.turnus)
    if filters.turnus and turnus is None:
        log_audit_denial(
            user=request.user,
            endpoint_kind="list",
            reason_code="scope_unavailable",
        )
        raise Http404
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
    snapshot_id = _snapshot_id(
        request.query_params.get("snapshot_id"), turnus_id=turnus_id,
    )
    queryset = filtered_audit_events(filters, turnus_id)
    queryset = queryset.filter(id__lte=snapshot_id).order_by("-occurred_at", "-id")
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
    event_rows = list(audit_list_projection(queryset)[start:start + page_size])
    try:
        events = [
            serialize_audit_list_event(
                row,
                turnus_label=str(turnus),
                details_turnus_id=turnus_id if filters.turnus else None,
            )
            for row in event_rows
        ]
    except InvalidAuditListProjection as error:
        raise AuditListUnavailable from error
    filter_values = filters.as_query_dict()
    if not filter_values["turnus"]:
        filter_values["turnus"] = str(turnus_id)
    export_query = urlencode({
        key: value for key, value in filter_values.items() if value
    })
    payload = {
        "authorized": True,
        "events": events,
        "filters": filter_values,
        "filter_options": {
            "turnuses": options,
            "actions": _distinct_values(
                turnus_id, "action", snapshot_id=snapshot_id,
            ),
            "outcomes": _distinct_values(
                turnus_id, "outcome", snapshot_id=snapshot_id,
            ),
            "resource_types": _distinct_values(
                turnus_id, "resource_type", snapshot_id=snapshot_id,
            ),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
            "snapshot_id": snapshot_id,
        },
        "export_url": (
            f"/api/audit-events/export/?{export_query}"
            if export_query else "/api/audit-events/export/"
        ),
    }
    return payload


CONTRACTS = {"audit-events": audit_events}
