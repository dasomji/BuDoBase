import json
import re
import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from budo_app.audit import (
    AuditEventData,
    actor_label_for_user,
    client_ip_from_request,
    record_audit_event,
)
from budo_app.models import Profil
from budo_app.read_contracts.domains.audit import (
    audit_filters,
    filtered_audit_events,
    serialize_audit_event,
)


def _json_line(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _safe_filename_label(label):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "turnus"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_audit_events(request):
    user = request.user
    if not (
        user.has_perm("budo_app.view_auditevent")
        and user.has_perm("budo_app.export_auditevent")
    ):
        raise PermissionDenied("Audit export permission required.")
    profile = Profil.objects.select_related("turnus").filter(user=user).first()
    if profile is None or profile.turnus is None:
        raise Http404
    turnus = profile.turnus
    queryset, filters = filtered_audit_events(request, turnus.id)
    exported = list(
        queryset.select_related("turnus").order_by("occurred_at", "id")
    )
    records = [{
        "record_type": "header",
        "schema": "budo.audit",
        "version": 1,
        "turnus": {"id": turnus.id, "label": str(turnus)},
    }]
    records.extend(serialize_audit_event(event) for event in exported)
    body = "\n".join(_json_line(record) for record in records) + "\n"

    request_id = (
        request.META.get("HTTP_X_REQUEST_ID", "").strip() or str(uuid.uuid4())
    )
    record_audit_event(AuditEventData(
        turnus=turnus,
        actor_id=user.id,
        actor_label=actor_label_for_user(user),
        action="audit.export",
        outcome="success",
        resource_type="audit_log",
        resource_id=str(turnus.id),
        resource_label=f"Audit log {turnus}",
        request_id=request_id,
        client_ip=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        details={
            "result_count": len(exported),
            "filter_count": sum(bool(value) for value in filters.values()),
        },
    ))

    response = HttpResponse(body, content_type="application/x-ndjson; charset=utf-8")
    filename = f"audit-{_safe_filename_label(str(turnus))}.log"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
