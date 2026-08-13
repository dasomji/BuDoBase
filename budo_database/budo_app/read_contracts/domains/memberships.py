from django.contrib.auth.models import User

from budo_app.models import Turnus, TurnusJoinRequest
from budo_app.join_requests import IDENTITY_VERIFICATION_WARNING
from budo_app.product_admin_policy import require_product_admin
from django.core.exceptions import PermissionDenied


def _display_name(user):
    return user.get_full_name().strip() or user.username


def _team_overview(request, *, admin_only):
    if admin_only:
        require_product_admin(request.user, "Admin team overview access denied.")
        turnuses = Turnus.objects.all()
    elif request.user.is_superuser:
        turnuses = Turnus.objects.all()
    else:
        led_turnus_ids = request.user.turnus_memberships.filter(
            functional_role="leitung"
        ).values_list("turnus_id", flat=True)
        turnuses = Turnus.objects.filter(pk__in=led_turnus_ids)
        if not turnuses.exists():
            raise PermissionDenied("Team management access denied.")
    turnuses = turnuses.prefetch_related(
        "memberships__user__profil",
        "join_requests__user__profil",
    ).order_by(
        "-turnus_beginn", "turnus_nr", "id"
    )
    years = {}
    for turnus in turnuses:
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
            })
        year = str(turnus.turnus_beginn.year)
        pending_requests = []
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
            "members": members,
            "request_summary": {"pending": len(pending_requests)},
            "pending_requests": pending_requests,
        })
    people = []
    people_source = User.objects.filter(is_active=True).prefetch_related("turnus_memberships__turnus")
    visible_turnus_ids = None if request.user.is_superuser else {
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
        "can_manage_leitung": request.user.is_superuser,
        "can_manage_memberships": True,
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
