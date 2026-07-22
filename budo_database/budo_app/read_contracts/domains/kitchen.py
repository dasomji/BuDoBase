from django.db.models import Prefetch

from budo_app.models import Kinder, Meal, Profil, Schwerpunkte
from budo_app.read_contracts.common import active_turnus_id, kid_full_name


def _kid(kid):
    return {
        "id": kid.id,
        "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
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


def _kid_dietary_category(kid):
    return "vegetarian" if kid.get_veggie_bool() else "flexitarian"


def _profile_dietary_category(profile):
    return {
        "ft": "flexitarian",
        "vt": "vegetarian",
        "vn": "vegan",
    }.get(profile.essen, "flexitarian")


def _dietary_counts(focus):
    counts = {"flexitarian": 0, "vegetarian": 0, "vegan": 0}
    for kid in focus.kitchen_kids:
        counts[_kid_dietary_category(kid)] += 1
    for profile in focus.kitchen_carers:
        counts[_profile_dietary_category(profile)] += 1
    return counts


def _intolerances(focus):
    return {
        "kids": [
            {
                "name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
                "diet": _kid_dietary_category(kid),
                "details": details,
            }
            for kid in focus.kitchen_kids
            if (details := kid.get_clean_special_food())
        ],
        "team": [
            {
                "name": profile.rufname,
                "diet": _profile_dietary_category(profile),
                "details": profile.allergien,
            }
            for profile in focus.kitchen_carers
            if profile.allergien
        ],
    }


def _focus(focus):
    return {
        "id": focus.id,
        "name": focus.swp_name,
        "week": focus.schwerpunktzeit.woche,
        "duration": focus.schwerpunktzeit.dauer,
        "kid_count": len(focus.kitchen_kids),
        "carer_count": len(focus.kitchen_carers),
        "carers": ", ".join(
            profile.rufname for profile in focus.kitchen_carers
        ),
        "dietary_counts": _dietary_counts(focus),
        "intolerances": _intolerances(focus),
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
        .select_related("schwerpunktzeit")
        .prefetch_related(
            Prefetch(
                "swp_kinder",
                queryset=(
                    Kinder.objects.filter(turnus_id=turnus_id)
                    .only(
                        "id",
                        "kid_vorname",
                        "kid_nachname",
                        "vegetarisch",
                        "special_food_description",
                    )
                    .order_by("kid_vorname", "kid_nachname", "id")
                ),
                to_attr="kitchen_kids",
            ),
            Prefetch(
                "betreuende",
                queryset=(
                    Profil.objects.filter(turnus_id=turnus_id)
                    .only("id", "rufname", "essen", "allergien")
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
