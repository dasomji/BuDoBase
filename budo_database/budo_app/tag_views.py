from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Auslagerorte, Tag
from .react_views import render_react_page
from .tag_icons import TAG_ICON_KEYS


def _error(detail, *, status=400):
    return Response({"code": "invalid_tag", "detail": detail}, status=status)


def _serialize(tag):
    return {"id": tag.id, "name": tag.name, "icon": tag.icon}


def _require_permission(request, permission):
    if not request.user.has_perm(permission):
        return Response(
            {"code": "permission_denied", "detail": "Keine Berechtigung."},
            status=403,
        )
    return None


def _values(request):
    name = request.data.get("name")
    icon = request.data.get("icon")
    if not isinstance(name, str) or not name.strip():
        return None, None, _error("Bitte einen Namen eingeben.")
    if icon not in TAG_ICON_KEYS:
        return None, None, _error("Bitte ein gültiges Symbol auswählen.")
    return name, icon, None


@login_required
@permission_required("budo_app.change_tag", raise_exception=True)
def tag_settings_page(request):
    return render_react_page(request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_tag(request):
    denied = _require_permission(request, "budo_app.change_tag")
    if denied:
        return denied
    name, icon, error = _values(request)
    if error:
        return error
    tag = Tag(name=name, icon=icon)
    try:
        tag.full_clean()
        tag.save()
    except (ValidationError, IntegrityError):
        return _error("Ein Tag mit diesem Namen existiert bereits.", status=409)
    return Response({"tag": _serialize(tag)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_tag(request, tag_id):
    denied = _require_permission(request, "budo_app.change_tag")
    if denied:
        return denied
    name, icon, error = _values(request)
    if error:
        return error
    tag = get_object_or_404(Tag, id=tag_id)
    tag.name = name
    tag.icon = icon
    try:
        tag.full_clean()
        tag.save(update_fields=["name", "icon"])
    except (ValidationError, IntegrityError):
        return _error("Ein Tag mit diesem Namen existiert bereits.", status=409)
    return Response({"tag": _serialize(tag)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_tag(request, tag_id):
    denied = _require_permission(request, "budo_app.delete_tag")
    if denied:
        return denied
    with transaction.atomic():
        tag = get_object_or_404(Tag.objects.select_for_update(), id=tag_id)
        affected = list(
            Auslagerorte.objects.select_for_update()
            .filter(primary_tag_id=tag.id)
            .values_list("id", flat=True)
        )
        deleted_name = tag.name
        tag.delete()
        for place in Auslagerorte.objects.filter(id__in=affected).prefetch_related("tags"):
            next_tag = place.tags.order_by(Lower("name"), "id").first()
            place.primary_tag = next_tag
            place.save(update_fields=["primary_tag"])
    return Response({"deleted": {"id": tag_id, "name": deleted_name}})
