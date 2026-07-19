from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import ErsteHilfeEintrag, Geld, Kinder, Notizen, Schwerpunkte
from budo_app.read_contracts.common import (
    active_turnus_id,
    kid_full_name,
    required_query_integer,
    serialize_datetime,
    serialize_first_aid_entry,
    serialize_money,
    serialize_note,
    serialize_transaction,
)


def _focus_queryset(turnus_id):
    return (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus_id=turnus_id)
        .select_related("schwerpunktzeit")
        .order_by(
            "schwerpunktzeit__woche",
            "swp_name",
            "id",
        )
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
        "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
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


def _detail_kid(kid):
    focus_names = _focus_names_by_week(kid)
    transactions = kid.geld.all()
    return {
        "id": kid.id,
        "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
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
        "notes": [serialize_note(note) for note in kid.route_notes],
        "first_aid_entries": [
            serialize_first_aid_entry(entry)
            for entry in kid.route_first_aid_entries
        ],
        "transactions": [
            serialize_transaction(transaction) for transaction in transactions
        ],
        "remaining_money": serialize_money(kid.get_remaining_taschengeld()),
        "deposit": kid.pfand,
    }


def kids_directory(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        return {"kids": []}

    focuses = _focus_queryset(turnus_id)
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

    focuses = _focus_queryset(turnus_id)
    notes = Notizen.objects.select_related("added_by").order_by(
        "date_added",
        "id",
    )
    first_aid_entries = ErsteHilfeEintrag.objects.select_related(
        "added_by"
    ).order_by("-date_added", "-id")
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
            Prefetch(
                "erste_hilfe_eintraege",
                queryset=first_aid_entries,
                to_attr="route_first_aid_entries",
            ),
            Prefetch("geld", queryset=transactions),
        )
    )
    kid = get_object_or_404(queryset, id=required_query_integer(request))
    return {"kids": [_detail_kid(kid)]}


CONTRACTS = {
    "kid-detail": kid_detail,
    "kids-directory": kids_directory,
}
