"""HTTP command for changing the user's approved Turnus context."""

from collections.abc import Mapping
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
from budo_app.models import SecurityAuditEvent, Turnus


POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807
MAX_REQUEST_ID_LENGTH = 255


def _request_id(request):
    raw = request.headers.get("X-Request-ID", "")
    if not isinstance(raw, str):
        return str(uuid4())
    sanitized = "".join(
        character for character in raw.strip()
        if character.isascii() and (character.isalnum() or character in "-._:")
    )[:MAX_REQUEST_ID_LENGTH]
    return sanitized or str(uuid4())


def _positive_bigint(value):
    if isinstance(value, bool):
        return None
    text = str(value)
    if not text.isascii() or not text.isdigit() or len(text) > 19:
        return None
    parsed = int(text)
    if parsed < 1 or parsed > POSTGRES_BIGINT_MAX:
        return None
    return parsed


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def turnus_selection(request):
    request_id = _request_id(request)
    previous = selected_turnus_for(request.user)
    if not isinstance(request.data, Mapping):
        _record_unscoped_rejection(request_id, "invalid")
        return Response({"code": "invalid_turnus_selection"}, status=400)
    value = request.data.get("turnus_id")
    turnus_id = _positive_bigint(value)
    if turnus_id is None:
        _record_unscoped_rejection(request_id, "invalid")
        return Response({"code": "invalid_turnus_selection"}, status=400)

    turnus = Turnus.objects.filter(pk=turnus_id).first()
    if turnus is None:
        _record_unscoped_rejection(request_id, "not_found", turnus_id)
        return Response({"code": "forbidden_turnus_selection"}, status=403)

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
                request_id=request_id,
                client_ip=client_ip_from_request(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                details={
                    "previous_turnus_id": previous.id if previous else None,
                    "selected_turnus_id": turnus.id,
                },
            ))
    except ValidationError:
        _record_unscoped_rejection(request_id, "forbidden", turnus.id)
        return Response({"code": "forbidden_turnus_selection"}, status=403)
    return Response({"selected_id": turnus.id})


def _record_unscoped_rejection(request_id, reason, attempted_turnus_id=None):
    SecurityAuditEvent.objects.create(
        actor_id=None,
        action="turnus.selection.switch",
        reason=reason,
        request_id=request_id,
        attempted_turnus_id=attempted_turnus_id,
    )
