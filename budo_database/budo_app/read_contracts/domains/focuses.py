from collections import defaultdict

from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import (
    Auslagerorte,
    Kinder,
    Meal,
    Profil,
    Schwerpunkte,
    Schwerpunktzeit,
)
from budo_app.read_contracts.common import (
    active_turnus_id,
    kid_full_name,
    required_query_integer,
)


def focus_dashboard(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"focuses": []}

    carers = (
        Profil.objects.filter(turnus_id=turnus_id)
        .only("id", "rufname")
        .order_by("rufname", "id")
    )
    focuses = (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus_id=turnus_id)
        .select_related("ort", "schwerpunktzeit")
        .prefetch_related(
            Prefetch("betreuende", queryset=carers, to_attr="route_carers"),
        )
        .annotate(
            kid_count=Count(
                "swp_kinder",
                filter=Q(swp_kinder__turnus_id=turnus_id),
                distinct=True,
            ),
            meals_assigned=Exists(
                Meal.objects.filter(
                    schwerpunkt_id=OuterRef("pk"),
                    meal_choice__gt="",
                ),
            ),
        )
        .order_by("schwerpunktzeit__woche", "swp_name", "id")
    )
    return {
        "focuses": [
            {
                "id": focus.id,
                "name": focus.swp_name,
                "week": focus.schwerpunktzeit.woche,
                "place_id": focus.ort_id,
                "place": focus.ort.name if focus.ort else None,
                "coordinates": focus.ort.koordinaten if focus.ort else "",
                "carers": ", ".join(carer.rufname for carer in focus.route_carers),
                "off_site": focus.auslagern,
                "kid_count": focus.kid_count,
                "meals_assigned": focus.meals_assigned,
            }
            for focus in focuses
        ],
    }


def _focus_queryset(turnus_id, *, with_kids=False, with_meals=False):
    carers = (
        Profil.objects.filter(turnus_id=turnus_id)
        .only("id", "rufname")
        .order_by("rufname", "id")
    )
    queryset = (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus_id=turnus_id)
        .select_related("ort", "schwerpunktzeit", "schwerpunktzeit__turnus")
        .prefetch_related(
            Prefetch("betreuende", queryset=carers, to_attr="route_carers"),
        )
    )
    if with_meals:
        queryset = queryset.prefetch_related(
            Prefetch(
                "meals",
                queryset=Meal.objects.order_by("day", "id"),
                to_attr="route_meals",
            ),
        )
    if with_kids:
        kids = (
            Kinder.objects.filter(turnus_id=turnus_id)
            .select_related("turnus")
            .order_by("kid_vorname", "kid_nachname", "id")
        )
        queryset = queryset.prefetch_related(
            Prefetch("swp_kinder", queryset=kids, to_attr="route_kids"),
        )
    return queryset


def _focus_detail(focus):
    meals = defaultdict(dict)
    for meal in focus.route_meals:
        meals[str(meal.day)][meal.meal_type] = meal.meal_choice
    return {
        "id": focus.id,
        "name": focus.swp_name,
        "description": focus.beschreibung,
        "week": focus.schwerpunktzeit.woche,
        "time": str(focus.schwerpunktzeit),
        "time_id": focus.schwerpunktzeit_id,
        "duration": focus.schwerpunktzeit.dauer,
        "start": focus.schwerpunktzeit.swp_beginn.isoformat(),
        "off_site": focus.auslagern,
        "place_id": focus.ort_id,
        "place": focus.ort.name if focus.ort else None,
        "coordinates": focus.ort.koordinaten if focus.ort else "",
        "carers": ", ".join(carer.rufname for carer in focus.route_carers),
        "carer_ids": [carer.id for carer in focus.route_carers],
        "meals": dict(meals),
    }


def _assigned_kid(kid):
    return {
        "id": kid.id,
        "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
        "present": kid.anwesend,
        "budo_family": kid.budo_family,
        "sex_short": kid.get_short_sex(),
        "age": kid.get_alter(),
        "birthday_during_turnus": kid.is_birthday_during_turnus(),
        "food": kid.get_food(),
        "drugs": kid.get_clean_drugs(),
        "illness": kid.get_clean_illness(),
    }


def focus_detail(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404
    focus = get_object_or_404(
        _focus_queryset(turnus_id, with_kids=True, with_meals=True),
        id=required_query_integer(request),
    )
    return {
        "focus": _focus_detail(focus),
        "kids": [_assigned_kid(kid) for kid in focus.route_kids],
    }


def _form_options(turnus_id):
    return {
        "places": list(
            Auslagerorte.objects.values("id", "name").order_by("name", "id"),
        ),
        "team": list(
            Profil.objects.filter(turnus_id=turnus_id)
            .values("id", "rufname")
            .order_by("rufname", "id"),
        ),
        "focus_times": [
            {
                "id": item.id,
                "label": str(item),
                "week": item.woche,
                "duration": item.dauer,
                "start": item.swp_beginn.isoformat(),
            }
            for item in Schwerpunktzeit.objects.filter(turnus_id=turnus_id)
            .select_related("turnus")
            .order_by("woche", "id")
        ],
    }


def focus_create(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"places": [], "team": [], "focus_times": []}
    return _form_options(turnus_id)


def _focus_form_value(focus):
    return {
        "id": focus.id,
        "name": focus.swp_name,
        "description": focus.beschreibung,
        "time_id": focus.schwerpunktzeit_id,
        "off_site": focus.auslagern,
        "place_id": focus.ort_id,
        "carer_ids": [carer.id for carer in focus.route_carers],
    }


def focus_update(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404
    focus = get_object_or_404(
        _focus_queryset(turnus_id),
        id=required_query_integer(request),
    )
    return {"focus": _focus_form_value(focus), **_form_options(turnus_id)}


def focus_meals(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404
    focus = get_object_or_404(
        _focus_queryset(turnus_id, with_meals=True),
        id=required_query_integer(request),
    )
    return {
        "focus": {
            "id": focus.id,
            "name": focus.swp_name,
            "meal_items": [
                {
                    "id": meal.id,
                    "day": meal.day,
                    "type": meal.meal_type,
                    "choice": meal.meal_choice,
                }
                for meal in focus.route_meals
            ],
        },
        "meal_choices": [
            {"value": "", "label": "---------"},
            {"value": "budo", "label": "BuDo"},
            {"value": "box", "label": "Box"},
            {"value": "warm", "label": "Warm"},
        ],
        "meal_types": dict(Meal.MEAL_TYPES),
    }


CONTRACTS = {
    "focus-create": focus_create,
    "focus-dashboard": focus_dashboard,
    "focus-detail": focus_detail,
    "focus-meals": focus_meals,
    "focus-update": focus_update,
}
