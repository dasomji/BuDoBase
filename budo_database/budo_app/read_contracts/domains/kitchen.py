from django.db.models import Prefetch

from budo_app.models import Kinder, Meal, Profil, Schwerpunkte
from budo_app.read_contracts.common import active_turnus_id


def _kid(kid):
    return {
        "id": kid.id,
        "full_name": str(kid),
        "present": kid.anwesend,
        "food": kid.get_food(),
        "special_food": kid.get_clean_special_food(),
    }


def _team_member(profile):
    return {
        "id": profile.id,
        "rufname": profile.rufname,
        "food_display": profile.get_food(),
        "allergies": profile.allergien,
    }


def _focus(focus):
    return {
        "id": focus.id,
        "name": focus.swp_name,
        "week": focus.schwerpunktzeit.woche,
        "duration": focus.schwerpunktzeit.dauer,
        "kid_count": len(focus.kitchen_kids),
        "carers": ", ".join(
            profile.rufname for profile in focus.kitchen_carers
        ),
        "place": focus.ort.name if focus.ort else None,
        "meals": [
            {
                "day": meal.day,
                "type": meal.meal_type,
                "choice": meal.meal_choice,
            }
            for meal in focus.kitchen_meals
        ],
    }


def build_kitchen_contract(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"kids": [], "team": [], "focuses": []}

    kids = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "anwesend",
            "vegetarisch",
            "special_food_description",
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    team = (
        Profil.objects.filter(turnus_id=turnus_id)
        .only("id", "rufname", "essen", "allergien")
        .order_by("rufname", "id")
    )
    focuses = (
        Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus_id=turnus_id,
            schwerpunktzeit__woche__in=("w1", "w2"),
        )
        .select_related("schwerpunktzeit", "ort")
        .prefetch_related(
            Prefetch(
                "swp_kinder",
                queryset=Kinder.objects.filter(
                    turnus_id=turnus_id,
                ).only("id"),
                to_attr="kitchen_kids",
            ),
            Prefetch(
                "betreuende",
                queryset=(
                    Profil.objects.filter(turnus_id=turnus_id)
                    .only("id", "rufname")
                    .order_by("rufname", "id")
                ),
                to_attr="kitchen_carers",
            ),
            Prefetch(
                "meals",
                queryset=Meal.objects.only(
                    "id",
                    "schwerpunkt_id",
                    "day",
                    "meal_type",
                    "meal_choice",
                ).order_by("day", "id"),
                to_attr="kitchen_meals",
            ),
        )
        .only(
            "id",
            "swp_name",
            "ort__id",
            "ort__name",
            "schwerpunktzeit__id",
            "schwerpunktzeit__woche",
            "schwerpunktzeit__dauer",
        )
        .order_by("schwerpunktzeit__woche", "swp_name", "id")
    )

    return {
        "kids": [_kid(kid) for kid in kids],
        "team": [_team_member(profile) for profile in team],
        "focuses": [_focus(focus) for focus in focuses],
    }


CONTRACTS = {
    "kitchen": build_kitchen_contract,
}
