import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from budo_app.audit import client_ip_from_request
from budo_app.audit_exports import (
    AuditExportCommand,
    AuditExportTurnusNotFound,
    export_audit_events as build_audit_export,
)
from budo_app.audit_queries import AuditFilters


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_audit_events(request):
    user = request.user
    if not (
        user.has_perm("budo_app.view_auditevent")
        and user.has_perm("budo_app.export_auditevent")
    ):
        raise PermissionDenied("Audit export permission required.")
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
        raise Http404

    response = StreamingHttpResponse(
        result.lines,
        content_type="application/x-ndjson; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{result.filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
