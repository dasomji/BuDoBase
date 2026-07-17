from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import Geld, Kinder, Notizen, Schwerpunkte
from budo_app.read_contracts.common import (
    active_turnus_id,
    required_query_integer,
    serialize_datetime,
    serialize_money,
)


def _focus_names_by_week(kid):
    return {
        focus.schwerpunktzeit.woche: focus.swp_name
        for focus in kid.route_focuses
        if focus.schwerpunktzeit_id
    }


def _directory_kid(kid):
    focus_names = _focus_names_by_week(kid)
    return {
        "id": kid.id,
        "full_name": f"{kid.kid_vorname} {kid.kid_nachname}".strip(),
        "present": kid.anwesend,
        "budo_family": kid.budo_family,
        "special_family": (
            str(kid.spezial_familien) if kid.spezial_familien else None
        ),
        "sex_short": kid.get_short_sex(),
        "age": kid.get_alter(),
        "birthday_during_turnus": kid.is_birthday_during_turnus(),
        "weeks": kid.turnus_dauer,
        "focus_w1": focus_names.get("w1", "---"),
        "focus_w2": focus_names.get("w2", "---"),
        "siblings": kid.get_clean_geschwister(),
        "tent_request": kid.get_clean_zeltwunsch(),
        "food": kid.get_food(),
        "drugs": kid.get_clean_drugs(),
        "illness": kid.get_clean_illness(),
        "note": kid.get_clean_anmerkung(),
        "booking_note": kid.get_clean_anmerkung_buchung(),
    }


def _note(note):
    return {
        "id": note.id,
        "text": note.notiz or "",
        "date": serialize_datetime(note.date_added),
        "day": note.date_added.strftime("%d.%m.") if note.date_added else "",
        "author": note.added_by.username,
    }


def _transaction(transaction):
    return {
        "id": transaction.id,
        "amount": serialize_money(transaction.amount),
        "date": serialize_datetime(transaction.date_added),
        "day": (
            transaction.date_added.strftime("%d.%m.")
            if transaction.date_added
            else ""
        ),
        "author": transaction.added_by.username,
    }


def _detail_kid(kid):
    focus_names = _focus_names_by_week(kid)
    pocket_money = sum(item.amount or 0 for item in kid.route_transactions)
    return {
        "id": kid.id,
        "full_name": f"{kid.kid_vorname} {kid.kid_nachname}".strip(),
        "present": kid.anwesend,
        "sex": kid.sex,
        "age": kid.get_alter(),
        "birthday": serialize_datetime(kid.kid_birthday),
        "weeks": kid.turnus_dauer,
        "siblings": kid.get_clean_geschwister(),
        "tent_request": kid.get_clean_zeltwunsch(),
        "budo_experience": kid.budo_erfahrung,
        "budo_family": kid.budo_family,
        "special_family": (
            str(kid.spezial_familien) if kid.spezial_familien else None
        ),
        "focus_w1": focus_names.get("w1", "---"),
        "focus_w2": focus_names.get("w2", "---"),
        "social_security_number": kid.sozialversicherungsnr,
        "illness": kid.get_clean_illness(),
        "drugs": kid.get_clean_drugs(),
        "vegetarian": kid.vegetarisch,
        "special_food": kid.get_clean_special_food(),
        "swimmer": kid.swimmer,
        "consent": kid.einverstaendnis_erklaerung,
        "over_the_counter_medication": kid.rezeptfreie_medikamente,
        "prescription_medication": kid.rezept_medikamente,
        "tetanus": kid.tetanusimpfung,
        "tick_vaccine": kid.zeckenimpfung,
        "organization": kid.anmelde_organisation,
        "registrant_name": (
            f"{kid.anmelder_vorname} {kid.anmelder_nachname}".strip()
        ),
        "registrant_email": kid.anmelder_email,
        "registrant_phone": kid.anmelder_mobil,
        "insured_with": kid.hauptversichert_bei,
        "emergency_contacts": kid.notfall_kontakte,
        "booking_note": kid.get_clean_anmerkung_buchung(),
        "note": kid.get_clean_anmerkung(),
        "notes": [_note(note) for note in kid.route_notes],
        "transactions": [
            _transaction(transaction) for transaction in kid.route_transactions
        ],
        "remaining_money": serialize_money(
            pocket_money - (kid.pfand * 0.25),
        ),
        "deposit": kid.pfand,
    }


def kids_directory(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}

    focuses = (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus_id=turnus_id)
        .select_related("schwerpunktzeit")
        .order_by(
            "schwerpunktzeit__woche",
            "swp_name",
            "id",
        )
    )
    kids = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .select_related("turnus", "spezial_familien")
        .prefetch_related(
            Prefetch("schwerpunkte", queryset=focuses, to_attr="route_focuses")
        )
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    return {"kids": [_directory_kid(kid) for kid in kids]}


def kid_detail(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404

    focuses = (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus_id=turnus_id)
        .select_related("schwerpunktzeit")
        .order_by(
            "schwerpunktzeit__woche",
            "swp_name",
            "id",
        )
    )
    notes = Notizen.objects.select_related("added_by").order_by(
        "date_added",
        "id",
    )
    transactions = Geld.objects.select_related("added_by").order_by(
        "date_added",
        "id",
    )
    queryset = (
        Kinder.objects.filter(turnus_id=turnus_id)
        .select_related("turnus", "spezial_familien")
        .prefetch_related(
            Prefetch("schwerpunkte", queryset=focuses, to_attr="route_focuses"),
            Prefetch("notizen", queryset=notes, to_attr="route_notes"),
            Prefetch("geld", queryset=transactions, to_attr="route_transactions"),
        )
    )
    kid = get_object_or_404(queryset, id=required_query_integer(request))
    return {"kids": [_detail_kid(kid)]}


CONTRACTS = {
    "kid-detail": kid_detail,
    "kids-directory": kids_directory,
}
