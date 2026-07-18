from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import BetreuerinnenGeld, Profil, Schwerpunkte, Turnus
from budo_app.read_contracts.common import (
    active_turnus_id,
    required_query_integer,
    serialize_money,
    serialize_utc_datetime,
)


def _can_change_turnus(user):
    return not user.groups.filter(name="Test-users").exists()


def _profile_queryset(turnus_id):
    focuses = Schwerpunkte.objects.none()
    if turnus_id is not None:
        focuses = (
            Schwerpunkte.objects.filter(
                schwerpunktzeit__turnus_id=turnus_id,
            )
            .only("id", "swp_name")
            .order_by("swp_name", "id")
        )
    money = BetreuerinnenGeld.objects.only(
        "id",
        "who_id",
        "amount",
        "what",
        "date_added",
    ).order_by("date_added", "id")
    return (
        Profil.objects.select_related("user")
        .prefetch_related(
            Prefetch("swp", queryset=focuses, to_attr="route_focuses"),
            Prefetch(
                "betreuerinnen_geld",
                queryset=money,
                to_attr="route_money_items",
            ),
        )
    )


def _profile(profile, *, can_change_turnus):
    money_items = [
        {
            "id": item.id,
            "amount": serialize_money(item.amount),
            "what": item.what,
            "date": serialize_utc_datetime(item.date_added),
        }
        for item in profile.route_money_items
    ]
    payload = {
        "id": profile.id,
        "email": profile.user.email,
        "rufname": profile.rufname,
        "phone": str(profile.telefonnummer),
        "allergies": profile.allergien,
        "coffee": profile.coffee,
        "role": profile.rolle,
        "role_display": profile.get_rolle(),
        "food": profile.essen,
        "food_display": profile.get_food(),
        "budo_family": profile.budo_family,
        "money_total": serialize_money(
            sum(item.amount or 0 for item in profile.route_money_items),
        ),
        "money_items": money_items,
    }
    if can_change_turnus is not None:
        payload["can_change_turnus"] = can_change_turnus
    return payload


def _focuses(profile):
    return [
        {"id": focus.id, "name": focus.swp_name}
        for focus in profile.route_focuses
    ]


def _turnuses(can_change_turnus):
    if not can_change_turnus:
        return []
    return [
        {"id": turnus.id, "label": str(turnus)}
        for turnus in Turnus.objects.order_by("-turnus_beginn", "-id")
    ]


def profile(request):
    turnus_id = active_turnus_id(request)
    own_profile = get_object_or_404(
        _profile_queryset(turnus_id),
        user_id=request.user.id,
    )
    can_change_turnus = _can_change_turnus(request.user)
    return {
        "profile": _profile(
            own_profile,
            can_change_turnus=can_change_turnus,
        ),
        "focuses": _focuses(own_profile),
        "turnuses": _turnuses(can_change_turnus),
    }


def teamer(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404
    selected_profile = get_object_or_404(
        _profile_queryset(turnus_id).filter(turnus_id=turnus_id),
        id=required_query_integer(request),
    )
    return {
        "person": _profile(
            selected_profile,
            can_change_turnus=None,
        ),
        "focuses": _focuses(selected_profile),
    }


CONTRACTS = {
    "profile": profile,
    "teamer": teamer,
}
