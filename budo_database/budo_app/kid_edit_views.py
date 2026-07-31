"""HTTP adapter for the atomic kid-edit command."""

from copy import deepcopy
import json

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from budo_app.audit import actor_label_for_user, client_ip_from_request
from budo_app.happy_cleaning_commands import CommandContext
from budo_app.kid_edit_commands import (
    KidEditCommandError,
    execute_kid_edit,
    validation_error_response,
)
from budo_app.kid_edit_contracts import (
    FIELD_CONTRACTS,
    KidEditParseError,
    canonicalize_storage_value,
    decode_kid_edit_request,
)
from budo_app.models import Kinder, Profil
from budo_app.react_views import render_react_page


@login_required
@require_GET
def kid_edit_page(request, kid_id):
    return render_react_page(request)


def _recover_field_command(request, error, profile, kid_id):
    field_names = {field.api_name for field in FIELD_CONTRACTS}
    if error.status != 422 or not set(error.errors).issubset(field_names):
        return None
    try:
        payload = deepcopy(json.loads(request.body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    child = Kinder.objects.filter(
        pk=kid_id, turnus_id=profile.turnus_id,
    ).only(*[field.storage_name for field in FIELD_CONTRACTS]).first()
    if child is None:
        return None
    by_api = {field.api_name: field for field in FIELD_CONTRACTS}
    for name in error.errors:
        field = by_api[name]
        payload["fields"][name] = canonicalize_storage_value(
            field, getattr(child, field.storage_name),
        ).api_value
    recovered = decode_kid_edit_request(
        json.dumps(payload).encode("utf-8"), "application/json",
    )
    return None if isinstance(recovered, KidEditParseError) else recovered


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def kid_edit(request, kid_id):
    decoded = decode_kid_edit_request(request.body, request.content_type)
    profile = (
        Profil.objects.select_related("turnus")
        .filter(user_id=request.user.id, turnus__isnull=False).first()
    )
    if profile is None:
        return Response({"ok": False, "code": "not_found"}, status=404)
    pre_errors = None
    if isinstance(decoded, KidEditParseError):
        recovered = _recover_field_command(request, decoded, profile, kid_id)
        if recovered is None:
            return Response(
                validation_error_response(decoded), status=decoded.status,
            )
        pre_errors = decoded.errors
        decoded = recovered
    context = CommandContext(
        turnus=profile.turnus,
        actor_id=request.user.id,
        actor_label=actor_label_for_user(request.user),
        request_id=decoded.request_id,
        client_ip=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    try:
        payload, status = execute_kid_edit(
            context=context, child_id=kid_id, decoded=decoded,
            pre_errors=pre_errors,
        )
    except KidEditCommandError as error:
        return Response(error.payload, status=error.status)
    return Response(payload, status=status)
