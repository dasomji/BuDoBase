"""Authenticated private read contract for the aggregate kid editor."""

from django.db.models import Count
from django.http import Http404

from budo_app.kid_edit_contracts import (
    FIELD_CONTRACTS,
    canonicalize_storage_value,
    sign_field_baseline,
    sign_legacy_preserve_value,
    sign_swp_baseline,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
)
from budo_app.read_contracts.common import (
    kid_full_name,
    require_active_turnus_id,
    required_query_integer,
)


_LEGACY_CONTROLLED_FIELDS = frozenset(
    {"sex", "stay_weeks", "vegetarian", "budo_family"}
)

_FIELD_OPTIONS = {
    "sex": [
        {"value": None, "label": "Nicht angegeben"},
        {"value": "female", "label": "weiblich"},
        {"value": "male", "label": "männlich"},
        {"value": "diverse", "label": "divers"},
    ],
    "stay_weeks": [
        {"value": None, "label": "Nicht angegeben"},
        {"value": 1, "label": "1 Woche"},
        {"value": 2, "label": "2 Wochen"},
    ],
    "budo_experience": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "vegetarian": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "consent": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "budo_family": [
        {"value": None, "label": "Nicht zugeordnet"},
        {"value": "S", "label": "Smallie"},
        {"value": "M", "label": "Medi"},
        {"value": "L", "label": "Largie"},
        {"value": "XL", "label": "X-largie"},
    ],
}


def _kid_fields(kid, turnus_id):
    fields = {}
    baselines = {}
    options = {
        field_name: [dict(option) for option in field_options]
        for field_name, field_options in _FIELD_OPTIONS.items()
    }
    for field in FIELD_CONTRACTS:
        raw_value = getattr(kid, field.storage_name)
        canonical = canonicalize_storage_value(field, raw_value)
        fields[field.api_name] = canonical.api_value
        baselines[field.api_name] = sign_field_baseline(
            turnus_id=turnus_id,
            child_id=kid.id,
            field_name=field.api_name,
            canonical_value=canonical.api_value,
        )
        if (
            field.api_name in _LEGACY_CONTROLLED_FIELDS
            and canonical.preserve_raw
            and canonical.legacy_kind == "unknown_choice"
        ):
            token = sign_legacy_preserve_value(
                turnus_id=turnus_id,
                child_id=kid.id,
                field_name=field.api_name,
                raw_storage_value=raw_value,
            )
            fields[field.api_name] = token
            options[field.api_name].insert(
                0,
                {
                    "value": token,
                    "label": f"Bisher: {canonical.api_value}",
                    "legacy": True,
                },
            )
    return fields, baselines, options


def _period_label(period):
    duration_unit = "Tag" if period.dauer == 1 else "Tage"
    return f"{period.get_woche_display()} ({period.dauer} {duration_unit})"


def _swp_periods(*, turnus_id, child_id):
    periods = list(
        Schwerpunktzeit.objects.filter(turnus_id=turnus_id)
        .only("id", "woche", "swp_beginn", "dauer", "turnus_id")
        .order_by("swp_beginn", "id")
    )
    if not periods:
        return []
    period_ids = [period.id for period in periods]
    focuses = list(
        Schwerpunkte.objects.filter(schwerpunktzeit_id__in=period_ids)
        .only("id", "swp_name", "schwerpunktzeit_id")
    )
    focuses_by_period = {period_id: [] for period_id in period_ids}
    for focus in focuses:
        focuses_by_period[focus.schwerpunktzeit_id].append(focus)
    for period_focuses in focuses_by_period.values():
        period_focuses.sort(key=lambda focus: (focus.swp_name.casefold(), focus.id))

    configured_focus_ids = [focus.id for focus in focuses]
    current_by_period = {period_id: [] for period_id in period_ids}
    if configured_focus_ids:
        through = Kinder.schwerpunkte.through
        current_rows = through.objects.filter(
            kinder_id=child_id,
            schwerpunkte_id__in=configured_focus_ids,
        ).values_list(
            "schwerpunkte_id",
            "schwerpunkte__schwerpunktzeit_id",
        )
        for focus_id, period_id in current_rows:
            current_by_period[period_id].append(focus_id)

    projected = []
    for period in periods:
        current_ids = tuple(sorted(current_by_period[period.id]))
        baseline = sign_swp_baseline(
            turnus_id=turnus_id,
            child_id=child_id,
            period_id=period.id,
            current_focus_ids=current_ids,
        )
        options = [
            {
                "target": {"kind": "unassigned"},
                "label": "Nicht eingeteilt",
            }
        ]
        options.extend(
            {
                "target": {"kind": "focus", "focus_id": focus.id},
                "label": focus.swp_name,
            }
            for focus in focuses_by_period[period.id]
        )
        if len(current_ids) > 1:
            submitted_target = {
                "kind": "preserve_legacy",
                "token": baseline,
            }
            current_id_set = set(current_ids)
            current_names = " + ".join(
                focus.swp_name
                for focus in focuses_by_period[period.id]
                if focus.id in current_id_set
            )
            legacy_label = (
                f"Bisher: {current_names} (Mehrfachzuordnung)"
            )
            target = {**submitted_target, "label": legacy_label}
            options.insert(
                0,
                {
                    "target": submitted_target,
                    "label": legacy_label,
                    "legacy": True,
                },
            )
        elif current_ids:
            target = {"kind": "focus", "focus_id": current_ids[0]}
        else:
            target = {"kind": "unassigned"}
        projected.append(
            {
                "id": period.id,
                "code": period.woche,
                "label": _period_label(period),
                "start": period.swp_beginn.isoformat(),
                "duration_days": period.dauer,
                "baseline": baseline,
                "target": target,
                "options": options,
            }
        )
    return projected


def _assignment_target(assignment):
    if assignment is None:
        return {"kind": "unassigned"}
    if assignment.is_excused:
        return {"kind": "excused"}
    return {"kind": "station", "station_id": assignment.station_id}


def _happy_cleaning_events(*, turnus_id, child_id):
    events = list(
        HappyCleaning.objects.filter(turnus_id=turnus_id)
        .only("id", "display_number", "revision", "turnus_id")
        .order_by("display_number", "id")
    )
    if not events:
        return []
    event_ids = [event.id for event in events]
    stations_by_event = {event_id: [] for event_id in event_ids}
    stations = (
        HappyCleaningStation.objects.filter(happy_cleaning_id__in=event_ids)
        .only(
            "id",
            "happy_cleaning_id",
            "name",
            "position",
            "max_kids",
        )
        .annotate(assigned_count=Count("assignments"))
        .order_by("happy_cleaning_id", "position", "id")
    )
    for station in stations:
        stations_by_event[station.happy_cleaning_id].append(station)
    assignments = {
        assignment.happy_cleaning_id: assignment
        for assignment in HappyCleaningAssignment.objects.filter(
            happy_cleaning_id__in=event_ids,
            child_id=child_id,
        ).only(
            "id",
            "happy_cleaning_id",
            "station_id",
            "target_kind",
            "version",
        )
    }

    projected = []
    for event in events:
        assignment = assignments.get(event.id)
        event_station_ids = {
            station.id for station in stations_by_event[event.id]
        }
        if (
            assignment is not None
            and not assignment.is_excused
            and assignment.station_id not in event_station_ids
        ):
            assignment = None
        target = _assignment_target(assignment)
        options = [
            {
                "target": {"kind": "unassigned"},
                "label": "Nicht eingeteilt",
                "can_select": True,
            },
            {
                "target": {"kind": "excused"},
                "label": "Entschuldigt",
                "can_select": True,
            },
        ]
        for station in stations_by_event[event.id]:
            is_current = (
                assignment is not None
                and not assignment.is_excused
                and assignment.station_id == station.id
            )
            assigned_count = station.assigned_count
            can_select = is_current or assigned_count < station.max_kids
            label = f"{station.name} · {assigned_count}/{station.max_kids}"
            if not can_select:
                label += " (voll)"
            options.append(
                {
                    "target": {
                        "kind": "station",
                        "station_id": station.id,
                    },
                    "label": label,
                    "station_id": station.id,
                    "station_name": station.name,
                    "position": station.position,
                    "max_kids": station.max_kids,
                    "assigned_count": assigned_count,
                    "free_seats": max(station.max_kids - assigned_count, 0),
                    "overbooked_count": max(
                        assigned_count - station.max_kids,
                        0,
                    ),
                    "can_select": can_select,
                    "is_current": is_current,
                }
            )
        projected.append(
            {
                "id": event.id,
                "display_number": event.display_number,
                "label": f"Happy Cleaning {event.display_number}",
                "revision": event.revision,
                "assignment_version": 0 if assignment is None else assignment.version,
                "target": target,
                "options": options,
            }
        )
    return projected


def kid_edit(request):
    turnus_id = require_active_turnus_id(request)
    child_id = required_query_integer(request)
    storage_fields = tuple(field.storage_name for field in FIELD_CONTRACTS)
    kid = (
        Kinder.objects.filter(pk=child_id, turnus_id=turnus_id)
        .only(
            "id",
            "turnus_id",
            "kid_vorname",
            "kid_nachname",
            "edit_version",
            "happy_cleaning_number",
            "happy_cleaning_number_version",
            *storage_fields,
        )
        .first()
    )
    if kid is None:
        raise Http404

    fields, baselines, options = _kid_fields(kid, turnus_id)
    return {
        "kid": {
            "id": kid.id,
            "full_name": kid_full_name(kid.kid_vorname, kid.kid_nachname),
            "edit_version": kid.edit_version,
            "fields": fields,
            "field_options": options,
            "field_baselines": baselines,
            "happy_cleaning_number": {
                "value": kid.happy_cleaning_number,
                "version": kid.happy_cleaning_number_version,
            },
            "swp_periods": _swp_periods(
                turnus_id=turnus_id,
                child_id=kid.id,
            ),
            "happy_cleaning_events": _happy_cleaning_events(
                turnus_id=turnus_id,
                child_id=kid.id,
            ),
        }
    }


CONTRACTS = {"kid-edit": kid_edit}
