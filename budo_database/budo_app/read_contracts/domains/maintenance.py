from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import Turnus


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


def _turnus_id(request):
    value = request.query_params.get("id")
    if not value or not str(value).isdigit():
        raise Http404
    return int(value)


def turnus_upload(request):
    turnus = get_object_or_404(
        Turnus.objects.only("id", "turnus_nr", "turnus_beginn"),
        id=_turnus_id(request),
    )
    return {"turnuses": [_turnus(turnus)]}


def special_upload(request):
    return {}


CONTRACTS = {
    "special-upload": special_upload,
    "turnus-list": turnus_list,
    "turnus-upload": turnus_upload,
}
