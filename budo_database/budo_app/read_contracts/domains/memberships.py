from django.core.exceptions import PermissionDenied

from budo_app.models import Turnus


def admin_team_overview(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Admin team overview access denied.")
    turnuses = Turnus.objects.prefetch_related("memberships__user__profil").order_by(
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
        years.setdefault(year, []).append({
            "id": turnus.id,
            "label": str(turnus),
            "number": turnus.turnus_nr,
            "start": turnus.turnus_beginn.isoformat(),
            "members": members,
            "request_summary": {"pending": 0},
        })
    return {"years": [{"year": int(year), "turnuses": items} for year, items in years.items()]}


CONTRACTS = {"admin-team-overview": admin_team_overview}
