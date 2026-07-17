from django.db.models import Count, Q

from budo_app.models import Kinder, Profil
from budo_app.utils import parse_sv_birthday


def _active_turnus_id(request):
    return (
        Profil.objects.filter(user_id=request.user.id)
        .values_list("turnus_id", flat=True)
        .first()
    )


def serial_letter(request):
    turnus_id = _active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}
    kids = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "ausweis",
            "e_card",
            "einverstaendnis_erklaerung",
            "rezeptfreie_medikamente",
            "rezept_medikamente",
            "tetanusimpfung",
            "zeckenimpfung",
            "illness",
            "drugs",
            "special_food_description",
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    return {
        "kids": [
            {
                "id": kid.id,
                "full_name": str(kid),
                "id_card": kid.ausweis,
                "e_card": kid.e_card,
                "consent": kid.einverstaendnis_erklaerung,
                "over_the_counter_medication": (
                    kid.rezeptfreie_medikamente
                ),
                "prescription_medication": kid.rezept_medikamente,
                "tetanus": kid.tetanusimpfung,
                "tick_vaccine": kid.zeckenimpfung,
                "illness": kid.get_clean_illness(),
                "drugs": kid.get_clean_drugs(),
                "special_food": kid.get_clean_special_food(),
            }
            for kid in kids
        ]
    }


def murder_game(request):
    turnus_id = _active_turnus_id(request)
    if turnus_id is None:
        return {"kids": [], "team": []}
    kids = (
        Kinder.objects.filter(turnus_id=turnus_id, anwesend=True)
        .values("id", "kid_vorname", "kid_nachname")
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    team = (
        Profil.objects.filter(turnus_id=turnus_id)
        .only("id", "rufname", "rolle")
        .order_by("rufname", "id")
    )
    return {
        "kids": [
            {
                "id": kid["id"],
                "full_name": (
                    f'{kid["kid_vorname"]} {kid["kid_nachname"]}'.strip()
                ),
            }
            for kid in kids
        ],
        "team": [
            {
                "id": member.id,
                "rufname": member.rufname,
                "role_display": member.get_rolle(),
            }
            for member in team
        ],
    }


def _family_kids(turnus_id, *, special):
    queryset = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .select_related("turnus", "spezial_familien")
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "kid_birthday",
            "anwesend",
            "budo_family",
            "spezial_familien__id",
            "spezial_familien__name",
            "spezial_familien__turnus_id",
            "turnus__id",
            "turnus__turnus_beginn",
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    if special:
        return queryset.filter(spezial_familien__turnus_id=turnus_id)
    return queryset.exclude(budo_family__isnull=True).exclude(budo_family="")


def _family_contract(request, *, special):
    turnus_id = _active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}
    family_key = "special_family" if special else "budo_family"
    kids = _family_kids(turnus_id, special=special)
    return {
        "kids": [
            {
                "id": kid.id,
                "full_name": str(kid),
                "present": kid.anwesend,
                "age": kid.get_alter(),
                family_key: (
                    kid.spezial_familien.name
                    if special
                    else kid.budo_family
                ),
            }
            for kid in kids
        ]
    }


def families(request):
    return _family_contract(request, special=False)


def special_families(request):
    return _family_contract(request, special=True)


def _birthday_kid(kid):
    try:
        calculated = parse_sv_birthday(kid.sozialversicherungsnr)
    except (TypeError, ValueError):
        calculated = None
    return {
        "id": kid.id,
        "full_name": str(kid),
        "present": kid.anwesend,
        "birthday": (
            kid.kid_birthday.isoformat() if kid.kid_birthday else None
        ),
        "sv_birthday": calculated.isoformat() if calculated else None,
    }


def birthdays(request):
    turnus_id = _active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}
    kids = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "anwesend",
            "kid_birthday",
            "sozialversicherungsnr",
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    return {
        "kids": [_birthday_kid(kid) for kid in kids]
    }


def kid_count(request):
    turnus_id = _active_turnus_id(request)
    if turnus_id is None:
        return {"totals": {"checked_in": 0, "kids": 0}}
    counts = Kinder.objects.filter(turnus_id=turnus_id).aggregate(
        kids=Count("id"),
        checked_in=Count("id", filter=Q(anwesend=True)),
    )
    return {"totals": counts}


CONTRACTS = {
    "birthdays": birthdays,
    "families": families,
    "kid-count": kid_count,
    "murder-game": murder_game,
    "serial-letter": serial_letter,
    "special-families": special_families,
}
