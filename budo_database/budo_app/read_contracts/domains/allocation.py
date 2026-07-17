from django.db.models import Prefetch
from rest_framework.exceptions import ParseError

from budo_app.models import Kinder, Schwerpunkte, SchwerpunktWahl


def build_allocation_contract(request):
    week_number = request.query_params.get("week")
    if week_number not in {"1", "2"}:
        raise ParseError("Allocation week must be 1 or 2.")

    week = f"w{week_number}"
    profile = getattr(request.user, "profil", None)
    turnus_id = profile.turnus_id if profile else None
    if turnus_id is None:
        return {"kids": [], "focuses": []}

    focuses = list(
        Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus_id=turnus_id,
            schwerpunktzeit__woche=week,
        )
        .values("id", "swp_name")
        .order_by("swp_name", "id")
    )
    kids = list(
        Kinder.objects.filter(turnus_id=turnus_id)
        .select_related("turnus")
        .prefetch_related(
            Prefetch(
                "schwerpunkte",
                queryset=Schwerpunkte.objects.filter(
                    schwerpunktzeit__turnus_id=turnus_id,
                    schwerpunktzeit__woche=week,
                ).only("id"),
                to_attr="allocation_focuses",
            ),
            Prefetch(
                "schwerpunkt_wahl",
                queryset=SchwerpunktWahl.objects.filter(
                    schwerpunktzeit__turnus_id=turnus_id,
                    schwerpunktzeit__woche=week,
                ),
                to_attr="allocation_choices",
            ),
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )

    focus_members = {focus["id"]: [] for focus in focuses}
    kid_items = []
    for kid in kids:
        focus_ids = [focus.id for focus in kid.allocation_focuses]
        for focus_id in focus_ids:
            focus_members[focus_id].append(kid.id)
        kid_items.append(
            {
                "id": kid.id,
                "full_name": str(kid),
                "age": kid.get_alter(),
                "siblings": kid.get_clean_geschwister(),
                "focus_ids": focus_ids,
                "choices": [
                    {
                        "week": week,
                        "first": (
                            choice.erste_wahl_id
                            if choice.erste_wahl_id in focus_members
                            else None
                        ),
                        "second": (
                            choice.zweite_wahl_id
                            if choice.zweite_wahl_id in focus_members
                            else None
                        ),
                        "third": (
                            choice.dritte_wahl_id
                            if choice.dritte_wahl_id in focus_members
                            else None
                        ),
                        "friends": choice.freunde,
                    }
                    for choice in kid.allocation_choices
                ],
            }
        )

    return {
        "kids": kid_items,
        "focuses": [
            {
                "id": focus["id"],
                "name": focus["swp_name"],
                "week": week,
                "kid_ids": focus_members[focus["id"]],
            }
            for focus in focuses
        ],
    }


CONTRACTS = {
    "allocation": build_allocation_contract,
}
