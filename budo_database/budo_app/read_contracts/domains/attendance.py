from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404

from budo_app.models import Geld, Kinder
from budo_app.read_contracts.common import (
    require_active_turnus_id,
    serialize_money,
)


def _requested_kid(request, *fields):
    try:
        kid_id = int(request.query_params.get("id", ""))
    except (TypeError, ValueError):
        raise Http404 from None

    kid = (
        Kinder.objects.filter(
            id=kid_id,
            turnus_id=require_active_turnus_id(request),
        )
        .values("id", "kid_vorname", "kid_nachname", *fields)
        .first()
    )
    if kid is None:
        raise Http404
    return kid


def _attendance_kid(kid):
    return {
        "id": kid["id"],
        "full_name": (
            f'{kid["kid_vorname"]} {kid["kid_nachname"]}'.strip()
        ),
        "present": kid["anwesend"],
        "id_card": kid["ausweis"],
        "e_card": kid["e_card"],
        "consent": kid["einverstaendnis_erklaerung"],
    }


def _selected_attendance_kid(request):
    return _requested_kid(
        request,
        "anwesend",
        "ausweis",
        "e_card",
        "einverstaendnis_erklaerung",
    )


def check_in(request):
    return {"kid": _attendance_kid(_selected_attendance_kid(request))}


def check_out(request):
    kid = _selected_attendance_kid(request)
    pocket_money = Geld.objects.filter(kinder_id=kid["id"]).aggregate(
        total=Sum("amount"),
    )["total"]
    return {
        "kid": {
            **_attendance_kid(kid),
            "pocket_money": serialize_money(pocket_money),
        },
    }


def _transport_kids(request):
    return Kinder.objects.filter(
        turnus_id=require_active_turnus_id(request),
    ).select_related("turnus").only(
        "id",
        "kid_vorname",
        "kid_nachname",
        "kid_birthday",
        "turnus_id",
        "turnus__turnus_beginn",
        "anwesend",
        "zug_anreise",
        "zug_abreise",
        "notiz_abreise",
        "top_jugendticket",
        "geschwister",
        "anmelder_vorname",
        "anmelder_nachname",
        "anmelder_mobil",
    )


def _transport_kid(kid):
    return {
        "id": kid.id,
        "full_name": f"{kid.kid_vorname} {kid.kid_nachname}".strip(),
        "present": kid.anwesend,
        "youth_ticket": kid.top_jugendticket,
        "age": kid.get_alter(),
        "registrant_name": (
            f"{kid.anmelder_vorname} {kid.anmelder_nachname}".strip()
        ),
        "registrant_phone": kid.anmelder_mobil,
        "siblings": kid.get_clean_geschwister(),
    }


def train_arrival(request):
    kids = list(
        _transport_kids(request)
        .filter(zug_anreise=True)
        .order_by("kid_vorname", "kid_nachname")
    )
    return {
        "kids": [
            {**_transport_kid(kid), "train_arrival": kid.zug_anreise}
            for kid in kids
        ],
        "totals": {
            "train_arrival": len(kids),
            "with_youth_ticket": sum(
                kid.top_jugendticket is True for kid in kids
            ),
            "without_youth_ticket": sum(
                kid.top_jugendticket is not True for kid in kids
            ),
        },
    }


def train_departure(request):
    kids = list(
        _transport_kids(request).order_by(
            Coalesce("zug_abreise", Value(False)).desc(),
            "kid_vorname",
            "kid_nachname",
        )
    )
    return {
        "kids": [
            {
                **_transport_kid(kid),
                "train_departure": kid.zug_abreise,
                "departure_note": kid.notiz_abreise,
            }
            for kid in kids
        ],
        "totals": {
            "train_departure": sum(
                kid.zug_abreise is True for kid in kids
            ),
        },
    }


CONTRACTS = {
    "check-in": check_in,
    "check-out": check_out,
    "train-arrival": train_arrival,
    "train-departure": train_departure,
}
