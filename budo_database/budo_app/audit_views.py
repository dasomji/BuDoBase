import uuid

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, StreamingHttpResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from budo_app.audit import (
    AuditEventData,
    actor_label_for_user,
    client_ip_from_request,
    record_audit_event,
)
from budo_app.audit_policy import (
    AuditDetailIsAuthenticated,
    AuditExportIsAuthenticated,
    can_export_audit,
    can_view_audit,
    log_audit_denial,
)
from budo_app.audit_exports import (
    AuditExportCommand,
    AuditExportTurnusNotFound,
    export_audit_events as build_audit_export,
)
from budo_app.audit_queries import (
    AuditFilters,
    selected_audit_turnus,
    serialize_audit_event,
)
from budo_app.models import AuditEvent
from budo_app.react_views import render_react_page


class AuditDetailUnavailable(APIException):
    status_code = 503
    default_detail = "Audit detail is temporarily unavailable."
    default_code = "audit_detail_unavailable"


@login_required
@require_GET
def audit_page(request):
    if not can_view_audit(request.user):
        log_audit_denial(
            user=request.user,
            endpoint_kind="list",
            reason_code="forbidden",
        )
        raise PermissionDenied("Audit access denied.")
    return render_react_page(request)


@api_view(["GET"])
@permission_classes([AuditDetailIsAuthenticated])
def audit_event_detail(request, event_id):
    user = request.user
    if not can_view_audit(user):
        log_audit_denial(
            user=user,
            endpoint_kind="detail",
            reason_code="forbidden",
        )
        raise PermissionDenied("Audit access denied.")

    requested_turnus = str(request.query_params.get("turnus", "")).strip()
    turnus = selected_audit_turnus(user, requested_turnus)
    if turnus is None:
        log_audit_denial(
            user=user,
            endpoint_kind="detail",
            reason_code="scope_unavailable",
        )
        raise Http404
    try:
        event = (
            AuditEvent.objects.select_related("turnus")
            .get(pk=event_id, turnus_id=turnus.id)
        )
    except AuditEvent.DoesNotExist:
        log_audit_denial(
            user=user,
            endpoint_kind="detail",
            reason_code="scope_unavailable",
        )
        raise Http404

    payload = serialize_audit_event(event)
    access = AuditEventData(
        turnus=turnus,
        actor_id=user.id,
        actor_label=actor_label_for_user(user),
        action="audit.view",
        outcome="success",
        resource_type="audit_event",
        resource_id=str(event.id),
        resource_label=f"Audit event {event.id}",
        request_id=(
            request.META.get("HTTP_X_REQUEST_ID", "").strip()
            or str(uuid.uuid4())
        ),
        client_ip=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        details={
            "view_kind": "detail",
            "result_count": 1,
            "filter_count": 0,
            "audit_event_id": event.id,
            "snapshot_id": event.id,
            "sensitive_payload_count": 1 if event.action == "kid.edit" else 0,
        },
    )
    try:
        record_audit_event(access)
    except Exception as error:
        raise AuditDetailUnavailable from error
    return Response(payload)


@api_view(["GET"])
@permission_classes([AuditExportIsAuthenticated])
def export_audit_events(request):
    user = request.user
    if not can_export_audit(user):
        log_audit_denial(
            user=user,
            endpoint_kind="export",
            reason_code="forbidden",
        )
        raise PermissionDenied("Audit access denied.")
    filters = AuditFilters.from_query_params(request.query_params)
    request_id = (
        request.META.get("HTTP_X_REQUEST_ID", "").strip() or str(uuid.uuid4())
    )
    try:
        result = build_audit_export(AuditExportCommand(
            user=user,
            filters=filters,
            request_id=request_id,
            client_ip=client_ip_from_request(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        ))
    except AuditExportTurnusNotFound:
        log_audit_denial(
            user=user,
            endpoint_kind="export",
            reason_code="scope_unavailable",
        )
        raise Http404

    response = StreamingHttpResponse(
        result.lines,
        content_type="application/x-ndjson; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{result.filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
