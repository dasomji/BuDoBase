"""HTTP command for changing the user's approved Turnus context."""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from budo_app.audit import (
    AuditEventData,
    actor_label_for_user,
    client_ip_from_request,
    record_audit_event,
)
from budo_app.memberships import select_turnus, selected_turnus_for
from budo_app.models import Turnus


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def turnus_selection(request):
    value = request.data.get("turnus_id")
    if isinstance(value, bool) or not str(value).isdigit():
        return Response({"code": "invalid_turnus_selection"}, status=400)

    turnus = Turnus.objects.filter(pk=int(value)).first()
    if turnus is None:
        return Response({"code": "forbidden_turnus_selection"}, status=403)

    previous = selected_turnus_for(request.user)
    try:
        with transaction.atomic():
            select_turnus(request.user, turnus)
            record_audit_event(AuditEventData(
                turnus=turnus,
                actor_id=request.user.id,
                actor_label=actor_label_for_user(request.user),
                action="turnus.selection.switch",
                outcome="success",
                resource_type="turnus_selection",
                resource_id=str(turnus.id),
                resource_label=f"Turnus selection {turnus.id}",
                request_id=request.headers.get("X-Request-ID") or str(uuid4()),
                client_ip=client_ip_from_request(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                details={
                    "previous_turnus_id": previous.id if previous else None,
                    "selected_turnus_id": turnus.id,
                },
            ))
    except ValidationError:
        return Response({"code": "forbidden_turnus_selection"}, status=403)
    return Response({"selected_id": turnus.id})
