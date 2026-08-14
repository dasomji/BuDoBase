from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from budo_app.models import Profil, Schwerpunkte, TurnusMembership
from budo_app.memberships import membership_role_display
from budo_app.read_contracts.common import (
    active_turnus_id,
    required_query_integer,
)


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
        Prefetch(
            "user__turnus_memberships",
            queryset=TurnusMembership.objects.filter(turnus_id=turnus_id),
            to_attr="route_memberships",
        ),
    )


def _profile_fields(profile, turnus_id=None):
    memberships = getattr(profile.user, "route_memberships", ())
    membership = memberships[0] if memberships else None
    return {
        "id": profile.id,
        "email": profile.user.email,
        "rufname": profile.rufname,
        "phone": str(profile.telefonnummer),
        "allergies": profile.allergien,
        "coffee": profile.coffee,
        "role": membership.functional_role if membership else "",
        "role_display": membership_role_display(membership) if membership else "",
        "food": profile.essen,
        "food_display": profile.get_food(),
        "budo_family": profile.budo_family,
    }


def _focuses(profile):
    return [
        {"id": focus.id, "name": focus.swp_name}
        for focus in profile.route_focuses
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
            _profile_queryset(turnus_id).filter(
                user__turnus_memberships__turnus_id=turnus_id,
            ),
            id=required_query_integer(request),
        )
    return {
        "profile": _profile_fields(selected_profile, turnus_id),
        "focuses": _focuses(selected_profile),
    }


def team(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"team": []}
    profiles = (
        _profile_queryset(turnus_id)
        .filter(user__turnus_memberships__turnus_id=turnus_id)
        .distinct()
        .order_by("rufname", "id")
    )
    return {
        "team": [
            {**_profile_fields(item, turnus_id), "focuses": _focuses(item)}
            for item in profiles
        ],
    }


CONTRACTS = {
    "profile": profile,
    "team": team,
}
