from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from budo_app.models import Turnus
from budo_app.read_contracts.common import required_query_integer


def _turnus(item):
    return {
        "id": item.id,
        "label": str(item),
        "number": item.turnus_nr,
        "start": item.turnus_beginn.isoformat(),
    }


def turnus_list(request):
    turnuses = Turnus.objects.only(
        "id",
        "turnus_nr",
        "turnus_beginn",
    ).order_by("-turnus_beginn", "-id")
    return {"turnuses": [_turnus(turnus) for turnus in turnuses]}


def turnus_upload(request):
    turnus = get_object_or_404(
        Turnus.objects.only("id", "turnus_nr", "turnus_beginn"),
        id=required_query_integer(request),
    )
    return {"turnuses": [_turnus(turnus)]}


def admin_settings(request):
    if not request.user.is_staff:
        raise PermissionDenied("Admin settings access denied.")
    return {}


CONTRACTS = {
    "admin-settings": admin_settings,
    "turnus-list": turnus_list,
    "turnus-upload": turnus_upload,
}
