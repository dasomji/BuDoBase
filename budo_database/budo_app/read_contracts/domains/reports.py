from django.db.models import Count, Q

from budo_app.models import Kinder, TurnusMembership
from budo_app.memberships import membership_role_display
from budo_app.read_contracts.common import active_turnus_id, kid_full_name
from budo_app.utils import parse_sv_birthday


def serial_letter(request):
    turnus_id = active_turnus_id(request)
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
                "full_name": kid_full_name(
                    kid.kid_vorname, kid.kid_nachname
                ),
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
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"kids": [], "team": []}
    kids = (
        Kinder.objects.filter(turnus_id=turnus_id, anwesend=True)
        .values("id", "kid_vorname", "kid_nachname")
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    team = TurnusMembership.objects.filter(turnus_id=turnus_id).select_related(
        "user__profil"
    ).order_by("user__profil__rufname", "id")
    return {
        "kids": [
            {
                "id": kid["id"],
                "full_name": kid_full_name(
                    kid["kid_vorname"], kid["kid_nachname"]
                ),
            }
            for kid in kids
        ],
        "team": [
            {
                "id": member.user.profil.id,
                "rufname": member.user.profil.rufname,
                "role_display": membership_role_display(member),
            }
            for member in team
        ],
    }


def _family_kids(turnus_id):
    return (
        Kinder.objects.filter(turnus_id=turnus_id)
        .select_related("turnus")
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "kid_birthday",
            "anwesend",
            "budo_family",
            "turnus__id",
            "turnus__turnus_beginn",
        )
        .exclude(budo_family__isnull=True)
        .exclude(budo_family="")
        .order_by("kid_vorname", "kid_nachname", "id")
    )


def families(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}
    return {
        "kids": [
            {
                "id": kid.id,
                "full_name": kid_full_name(
                    kid.kid_vorname, kid.kid_nachname
                ),
                "present": kid.anwesend,
                "age": kid.get_alter(),
                "budo_family": kid.budo_family,
            }
            for kid in _family_kids(turnus_id)
        ]
    }


def _birthday_kid(kid):
    try:
        calculated = parse_sv_birthday(kid.sozialversicherungsnr)
    except (TypeError, ValueError):
        calculated = None
    return {
        "id": kid.id,
        "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
        "present": kid.anwesend,
        "birthday": (
            kid.kid_birthday.isoformat() if kid.kid_birthday else None
        ),
        "sv_birthday": calculated.isoformat() if calculated else None,
    }


def birthdays(request):
    turnus_id = active_turnus_id(request)
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
    turnus_id = active_turnus_id(request)
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
}
