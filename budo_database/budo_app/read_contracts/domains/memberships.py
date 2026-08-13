from django.contrib.auth.models import User

from budo_app.models import Turnus, TurnusJoinRequest
from budo_app.product_admin_policy import require_product_admin


def admin_team_overview(request):
    require_product_admin(request.user, "Admin team overview access denied.")
    turnuses = Turnus.objects.prefetch_related(
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
            key=lambda item: (item.functional_role != "leitung", item.user.get_full_name().casefold(), item.user.username.casefold()),
        ):
            name = membership.user.get_full_name().strip() or membership.user.username
            members.append({
                "id": membership.id,
                "user_id": membership.user_id,
                "name": name,
                "functional_role": membership.functional_role,
                "role_label": membership.get_functional_role_display(),
                "team_label": membership.team_label,
            })
        year = str(turnus.turnus_beginn.year)
        pending_requests = []
        for join_request in turnus.join_requests.all():
            if join_request.status != TurnusJoinRequest.Status.PENDING:
                continue
            name = join_request.user.get_full_name().strip() or join_request.user.username
            pending_requests.append({"id": join_request.id, "user_id": join_request.user_id, "name": name})
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
    for user in User.objects.filter(is_active=True).prefetch_related("turnus_memberships__turnus"):
        name = user.get_full_name().strip() or user.username
        relationships = [str(item.turnus) for item in user.turnus_memberships.all()]
        people.append({
            "id": user.id,
            "name": name,
            "relationships": sorted(relationships, key=str.casefold),
            "available": not relationships,
        })
    people.sort(key=lambda item: item["name"].casefold())
    return {
        "years": [{"year": int(year), "turnuses": items} for year, items in years.items()],
        "people": people,
    }


CONTRACTS = {"admin-team-overview": admin_team_overview}
