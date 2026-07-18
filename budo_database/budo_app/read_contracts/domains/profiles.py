from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from budo_app.models import Profil, Schwerpunkte, Turnus
from budo_app.read_contracts.common import (
    active_turnus_id,
    required_query_integer,
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
    return Profil.objects.select_related("user").prefetch_related(
        Prefetch("swp", queryset=focuses, to_attr="route_focuses"),
    )


def _profile_fields(profile):
    return {
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
    }


def _profile(profile, *, can_change_turnus):
    payload = _profile_fields(profile)
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
    selected_id = request.query_params.get("id")
    if selected_id is None:
        selected_profile = get_object_or_404(
            _profile_queryset(turnus_id),
            user_id=request.user.id,
        )
    else:
        if not request.user.has_perm("budo_app.change_profil"):
            raise PermissionDenied
        selected_profile = get_object_or_404(
            _profile_queryset(turnus_id),
            id=required_query_integer(request),
        )
    can_change_turnus = _can_change_turnus(request.user)
    return {
        "profile": _profile(
            selected_profile,
            can_change_turnus=can_change_turnus,
        ),
        "focuses": _focuses(selected_profile),
        "turnuses": _turnuses(can_change_turnus),
    }


def team(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"team": []}
    profiles = (
        _profile_queryset(turnus_id)
        .filter(turnus_id=turnus_id)
        .order_by("rufname", "id")
    )
    return {
        "team": [
            {**_profile_fields(item), "focuses": _focuses(item)}
            for item in profiles
        ],
    }


CONTRACTS = {
    "profile": profile,
    "team": team,
}
