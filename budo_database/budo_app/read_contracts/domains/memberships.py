from django.contrib.auth.models import User
from django.db.models import Prefetch

from budo_app.models import Schwerpunkte, Turnus, TurnusJoinRequest
from budo_app.join_requests import IDENTITY_VERIFICATION_WARNING
from budo_app.memberships import membership_role_display
from budo_app.product_admin_policy import require_product_admin


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
    if admin_only:
        require_product_admin(request.user, "Admin team overview access denied.")

    actor_memberships = {
        membership["turnus_id"]: membership["functional_role"]
        for membership in request.user.turnus_memberships.values(
            "turnus_id", "functional_role"
        )
    }
    managed_turnus_ids = {
        turnus_id
        for turnus_id, role in actor_memberships.items()
        if role == "leitung"
    }
    turnuses = list(Turnus.objects.prefetch_related(
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

    full_team_turnus_ids = (
        {turnus.id for turnus in turnuses}
        if global_admin
        else set(actor_memberships)
    )
    visible_turnuses_by_user = {}
    for turnus in turnuses:
        if turnus.id not in full_team_turnus_ids:
            continue
        for membership in turnus.memberships.all():
            visible_turnuses_by_user.setdefault(membership.user_id, []).append(str(turnus))

    years = {}
    for turnus in turnuses:
        can_view_team = global_admin or turnus.id in actor_memberships
        can_manage_memberships = global_admin or turnus.id in managed_turnus_ids
        ordered_memberships = sorted(
            turnus.memberships.all(),
            key=lambda item: (
                item.functional_role != "leitung",
                _display_name(item.user).casefold(),
            ),
        )
        leads = [
            {"name": _display_name(membership.user)}
            for membership in ordered_memberships
            if membership.functional_role == "leitung"
        ]
        members = []
        if can_view_team:
            for membership in ordered_memberships:
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

        own_requests = [
            join_request
            for join_request in turnus.join_requests.all()
            if join_request.user_id == request.user.id
        ]
        request_status = (
            TurnusJoinRequest.Status.APPROVED
            if turnus.id in actor_memberships
            else own_requests[0].status if own_requests else None
        )
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

        year = str(turnus.turnus_beginn.year)
        years.setdefault(year, []).append({
            "id": turnus.id,
            "label": str(turnus),
            "number": turnus.turnus_nr,
            "start": turnus.turnus_beginn.isoformat(),
            "end": turnus.get_turnus_ende().isoformat(),
            "excel_uploaded": bool(turnus.uploadedFile) if can_view_team else False,
            "members": members,
            "leads": leads,
            "can_view_team": can_view_team,
            "is_member": turnus.id in actor_memberships,
            "request_status": request_status,
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
        visible_turnus_ids = None if global_admin else managed_turnus_ids
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
