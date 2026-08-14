from django.contrib.auth.models import User
from django.db.models import Prefetch

from budo_app.models import Schwerpunkte, Turnus, TurnusJoinRequest
from budo_app.join_requests import IDENTITY_VERIFICATION_WARNING
from budo_app.memberships import membership_role_display
from budo_app.product_admin_policy import require_product_admin
from django.core.exceptions import PermissionDenied


def _display_name(user):
    profile = getattr(user, "profil", None)
    profile_name = (getattr(profile, "rufname", "") or "").strip()
    return profile_name or user.get_full_name().strip() or user.username


def _profile_card(membership, turnus_id, visible_turnus_labels):
    profile = membership.user.profil
    focuses = [
        {"id": focus.id, "name": focus.swp_name}
        for focus in profile.swp.all()
        if focus.schwerpunktzeit.turnus_id == turnus_id
    ]
    focuses.sort(key=lambda item: (item["name"].casefold(), item["id"]))
    return {
        "id": profile.id,
        "email": membership.user.email,
        "rufname": profile.rufname,
        "phone": str(profile.telefonnummer),
        "allergies": profile.allergien,
        "coffee": profile.coffee,
        "role": membership.functional_role,
        "role_display": membership_role_display(membership),
        "food": profile.essen,
        "food_display": profile.get_food(),
        "budo_family": profile.budo_family,
        "turnuses": visible_turnus_labels,
        "focuses": focuses,
    }


def _team_overview(request, *, admin_only):
    global_admin = request.user.is_superuser
    managed_turnus_ids = set()
    if admin_only:
        require_product_admin(request.user, "Admin team overview access denied.")
        turnuses = Turnus.objects.all()
    elif global_admin:
        turnuses = Turnus.objects.all()
    else:
        actor_memberships = request.user.turnus_memberships.values(
            "turnus_id", "functional_role"
        )
        visible_turnus_ids = []
        for membership in actor_memberships:
            visible_turnus_ids.append(membership["turnus_id"])
            if membership["functional_role"] == "leitung":
                managed_turnus_ids.add(membership["turnus_id"])
        if not visible_turnus_ids:
            raise PermissionDenied("Team management access denied.")
        turnuses = Turnus.objects.filter(pk__in=visible_turnus_ids)
    turnuses = list(turnuses.prefetch_related(
        "memberships__user__profil",
        Prefetch(
            "memberships__user__profil__swp",
            queryset=Schwerpunkte.objects.select_related("schwerpunktzeit").order_by(
                "swp_name", "id"
            ),
        ),
        "join_requests__user__profil",
    ).order_by(
        "-turnus_beginn", "turnus_nr", "id"
    ))
    visible_turnuses_by_user = {}
    for turnus in turnuses:
        for membership in turnus.memberships.all():
            visible_turnuses_by_user.setdefault(membership.user_id, []).append(str(turnus))
    years = {}
    for turnus in turnuses:
        can_manage_memberships = global_admin or turnus.id in managed_turnus_ids
        members = []
        for membership in sorted(
            turnus.memberships.all(),
            key=lambda item: (item.functional_role != "leitung", _display_name(item.user).casefold()),
        ):
            members.append({
                "id": membership.id,
                "user_id": membership.user_id,
                "name": _display_name(membership.user),
                "functional_role": membership.functional_role,
                "role_label": membership.get_functional_role_display(),
                "team_label": membership.team_label,
                "profile": _profile_card(
                    membership,
                    turnus.id,
                    visible_turnuses_by_user[membership.user_id],
                ),
            })
        year = str(turnus.turnus_beginn.year)
        pending_requests = []
        if can_manage_memberships:
            for join_request in turnus.join_requests.all():
                if join_request.status != TurnusJoinRequest.Status.PENDING:
                    continue
                pending_requests.append({
                    "id": join_request.id,
                    "user_id": join_request.user_id,
                    "name": _display_name(join_request.user),
                    "email": join_request.user.email,
                })
            pending_requests.sort(key=lambda item: item["name"].casefold())
        years.setdefault(year, []).append({
            "id": turnus.id,
            "label": str(turnus),
            "number": turnus.turnus_nr,
            "start": turnus.turnus_beginn.isoformat(),
            "end": turnus.get_turnus_ende().isoformat(),
            "excel_uploaded": bool(turnus.uploadedFile),
            "members": members,
            "request_summary": {"pending": len(pending_requests)},
            "pending_requests": pending_requests,
            "can_manage_memberships": can_manage_memberships,
            "can_edit_profiles": can_manage_memberships,
        })
    people = []
    if global_admin or managed_turnus_ids:
        people_source = (
            User.objects.filter(is_active=True)
            .select_related("profil")
            .prefetch_related("turnus_memberships__turnus")
        )
        visible_turnus_ids = None if global_admin else {
            turnus.id for turnus in turnuses
        }
        for user in people_source:
            visible_memberships = [
                item for item in user.turnus_memberships.all()
                if visible_turnus_ids is None or item.turnus_id in visible_turnus_ids
            ]
            relationships = [str(item.turnus) for item in visible_memberships]
            people.append({
                "id": user.id,
                "name": _display_name(user),
                "email": user.email,
                "relationships": sorted(relationships, key=str.casefold),
                "available": not relationships,
                # Memberships outside the actor's management scope deliberately do
                # not leak through labels, IDs, or availability state.
                "turnus_ids": [item.turnus_id for item in visible_memberships],
            })
        people.sort(key=lambda item: item["name"].casefold())
    return {
        "years": [{"year": int(year), "turnuses": items} for year, items in years.items()],
        "people": people,
        "can_manage_leitung": global_admin,
        "can_manage_memberships": global_admin or bool(managed_turnus_ids),
        "can_create_turnus": global_admin or bool(managed_turnus_ids),
        "identity_verification_warning": IDENTITY_VERIFICATION_WARNING,
    }


def admin_team_overview(request):
    return _team_overview(request, admin_only=True)


def team_management(request):
    return _team_overview(request, admin_only=False)


CONTRACTS = {
    "admin-team-overview": admin_team_overview,
    "team-management": team_management,
}
