from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import (
    ErsteHilfeEintrag,
    ErsteHilfeFoto,
    Geld,
    HappyCleaning,
    HappyCleaningAssignment,
    Kinder,
    Notizen,
    NotizFoto,
    Schwerpunkte,
    Schwerpunktzeit,
)
from budo_app.read_contracts.common import (
    active_turnus_id,
    kid_full_name,
    require_active_turnus_id,
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


def _period_label(period):
    duration_unit = "Tag" if period.dauer == 1 else "Tage"
    return f"{period.get_woche_display()} ({period.dauer} {duration_unit})"


def _detail_focus_assignments(kid):
    focuses_by_period = {
        period.id: [] for period in kid.turnus.route_focus_periods
    }
    for focus in kid.route_focuses:
        focuses_by_period[focus.schwerpunktzeit_id].append(focus)
    for focuses in focuses_by_period.values():
        focuses.sort(key=lambda focus: (focus.swp_name.casefold(), focus.id))
    return [
        {
            "period_id": period.id,
            "code": period.woche,
            "label": _period_label(period),
            "focuses": [
                {"id": focus.id, "label": focus.swp_name}
                for focus in focuses_by_period[period.id]
            ],
        }
        for period in kid.turnus.route_focus_periods
    ]


def _happy_cleaning_target(assignment):
    if assignment is None:
        return {"kind": "unassigned", "label": "Nicht eingeteilt"}
    if assignment.is_excused:
        return {"kind": "excused", "label": "Entschuldigt"}
    if (
        assignment.station_id is None
        or assignment.station.happy_cleaning_id
        != assignment.happy_cleaning_id
    ):
        return {"kind": "unassigned", "label": "Nicht eingeteilt"}
    return {
        "kind": "station",
        "station_id": assignment.station_id,
        "label": assignment.station.name,
    }


def _detail_happy_cleaning_assignments(kid):
    return [
        {
            "event_id": event.id,
            "display_number": event.display_number,
            "label": f"Happy Cleaning {event.display_number}",
            "target": _happy_cleaning_target(
                event.route_child_assignments[0]
                if event.route_child_assignments
                else None
            ),
        }
        for event in kid.turnus.route_happy_cleaning_events
    ]


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
    transactions = kid.geld.all()
    child_name = kid_full_name(kid.kid_vorname, kid.kid_nachname)
    return {
        "id": kid.id,
        "full_name": child_name,
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
        "focus_assignments": _detail_focus_assignments(kid),
        "happy_cleaning_number": kid.happy_cleaning_number,
        "happy_cleaning_assignments": (
            _detail_happy_cleaning_assignments(kid)
        ),
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
        "notes": [serialize_note(note, child_name) for note in kid.route_notes],
        "first_aid_entries": [
            serialize_first_aid_entry(entry, child_name)
            for entry in kid.route_first_aid_entries
        ],
        "transactions": [
            serialize_transaction(transaction) for transaction in transactions
        ],
        "remaining_money": serialize_money(kid.get_remaining_taschengeld()),
        "deposit": kid.pfand,
    }


def kids_directory(request):
    turnus_id = require_active_turnus_id(request)

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

    child_id = required_query_integer(request)
    focuses = _focus_queryset(turnus_id)
    focus_periods = Schwerpunktzeit.objects.filter(
        turnus_id=turnus_id,
    ).only(
        "id",
        "turnus_id",
        "woche",
        "swp_beginn",
        "dauer",
    ).order_by("swp_beginn", "id")
    child_assignments = (
        HappyCleaningAssignment.objects.filter(child_id=child_id)
        .select_related("station")
        .only(
            "id",
            "happy_cleaning_id",
            "station_id",
            "target_kind",
            "station__id",
            "station__name",
            "station__happy_cleaning_id",
        )
    )
    happy_cleaning_events = (
        HappyCleaning.objects.filter(turnus_id=turnus_id)
        .only("id", "turnus_id", "display_number")
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=child_assignments,
                to_attr="route_child_assignments",
            )
        )
        .order_by("display_number", "id")
    )
    note_photos = NotizFoto.objects.only(
        "id", "eintrag_id", "position", "width", "height"
    ).order_by("position", "id")
    notes = (
        Notizen.objects.select_related("added_by")
        .prefetch_related(Prefetch("fotos", queryset=note_photos, to_attr="route_photos"))
        .order_by("date_added", "id")
    )
    photos = ErsteHilfeFoto.objects.only(
        "id",
        "eintrag_id",
        "position",
        "width",
        "height",
    ).order_by("position", "id")
    first_aid_entries = (
        ErsteHilfeEintrag.objects.select_related("added_by")
        .prefetch_related(
            Prefetch("fotos", queryset=photos, to_attr="route_photos")
        )
        .order_by("-date_added", "-id")
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
            Prefetch(
                "turnus__schwerpunktzeit_set",
                queryset=focus_periods,
                to_attr="route_focus_periods",
            ),
            Prefetch(
                "turnus__happy_cleanings",
                queryset=happy_cleaning_events,
                to_attr="route_happy_cleaning_events",
            ),
            Prefetch("notizen", queryset=notes, to_attr="route_notes"),
            Prefetch(
                "erste_hilfe_eintraege",
                queryset=first_aid_entries,
                to_attr="route_first_aid_entries",
            ),
            Prefetch("geld", queryset=transactions),
        )
    )
    kid = get_object_or_404(queryset, id=child_id)
    return {"kids": [_detail_kid(kid)]}


CONTRACTS = {
    "kid-detail": kid_detail,
    "kids-directory": kids_directory,
}
