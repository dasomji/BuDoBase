"""Preflight storage-faithful kid-edit audit payloads without printing values."""

from collections import defaultdict
import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from budo_app.kid_edit_audit import (
    MAX_KID_EDIT_AUDIT_BYTES,
    _STORAGE_FIELDS,
    _event,
    _field_value,
    _period,
)
from budo_app.kid_edit_audit_snapshot import (
    LoadedKidEditAssignment,
    LoadedKidEditEvent,
    LoadedKidEditFocusLink,
    LoadedKidEditPeriod,
    build_kid_edit_audit_details,
    serialize_kid_edit_snapshot,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    Kinder,
    Schwerpunktzeit,
    Turnus,
)


def _period_label(period):
    unit = "Tag" if period.dauer == 1 else "Tage"
    return f"{period.get_woche_display()} ({period.dauer} {unit})"


def _encoded_size(value):
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        return 0
    return len(encoded)


def _unsupported_snapshot_path(snapshot):
    if type(snapshot) is not dict:
        return "$"
    fields = snapshot.get("fields")
    if type(fields) is not dict:
        return "fields"
    for name in _STORAGE_FIELDS:
        if name not in fields:
            return f"fields.{name}"
    unknown_fields = sorted(
        key
        for key in fields
        if type(key) is str and key not in _STORAGE_FIELDS
    )
    if unknown_fields:
        return f"fields.{unknown_fields[0]}"
    if any(type(key) is not str for key in fields):
        return "fields"
    for name in _STORAGE_FIELDS:
        try:
            _field_value(name, fields.get(name))
        except ValidationError:
            return f"fields.{name}"
    periods = snapshot.get("swp")
    if type(periods) is not list:
        return "swp"
    for index, period in enumerate(periods):
        try:
            _period(period)
        except (ValidationError, TypeError, ValueError):
            return f"swp.{index}"
    events = snapshot.get("happy_cleaning")
    if type(events) is not list:
        return "happy_cleaning"
    for index, event in enumerate(events):
        try:
            _event(event)
        except (ValidationError, TypeError, ValueError):
            return f"happy_cleaning.{index}"
    return "$"


def _loaded_inputs(children):
    child_ids = [child.pk for child in children]
    turnus_ids = {
        child.turnus_id for child in children if child.turnus_id is not None
    }

    periods_by_turnus = defaultdict(list)
    period_turnus = {}
    periods = Schwerpunktzeit.objects.filter(
        turnus_id__in=turnus_ids,
    ).order_by("swp_beginn", "id")
    for period in periods:
        periods_by_turnus[period.turnus_id].append(
            LoadedKidEditPeriod(
                period.id,
                period.woche,
                _period_label(period),
                period.swp_beginn,
                period.dauer,
            )
        )
        period_turnus[period.id] = period.turnus_id

    child_turnus = {child.pk: child.turnus_id for child in children}
    focuses_by_child = defaultdict(list)
    through = Kinder.schwerpunkte.through
    focus_rows = through.objects.filter(
        kinder_id__in=child_ids,
    ).values_list(
        "kinder_id",
        "schwerpunkte__schwerpunktzeit_id",
        "schwerpunkte_id",
        "schwerpunkte__swp_name",
    )
    for child_id, period_id, focus_id, label in focus_rows:
        if period_turnus.get(period_id) != child_turnus[child_id]:
            continue
        focuses_by_child[child_id].append(
            LoadedKidEditFocusLink(period_id, focus_id, label)
        )

    events_by_turnus = defaultdict(list)
    event_turnus = {}
    events = HappyCleaning.objects.filter(
        turnus_id__in=turnus_ids,
    ).order_by("display_number", "id")
    for event in events:
        events_by_turnus[event.turnus_id].append(
            LoadedKidEditEvent(
                event.id,
                event.display_number,
                f"Happy Cleaning {event.display_number}",
                event.revision,
            )
        )
        event_turnus[event.id] = event.turnus_id

    assignments_by_child = defaultdict(list)
    assignments = (
        HappyCleaningAssignment.objects.filter(
            child_id__in=child_ids,
            happy_cleaning_id__in=event_turnus,
        )
        .select_related("station")
        .order_by("happy_cleaning_id", "id")
    )
    for assignment in assignments:
        if event_turnus.get(assignment.happy_cleaning_id) != child_turnus[
            assignment.child_id
        ]:
            continue
        if assignment.is_excused:
            loaded = LoadedKidEditAssignment(
                assignment.happy_cleaning_id,
                assignment.version,
                "excused",
            )
        else:
            station = assignment.station
            loaded = LoadedKidEditAssignment(
                assignment.happy_cleaning_id,
                assignment.version,
                "station",
                assignment.station_id,
                station.name,
                station.happy_cleaning_id,
            )
        assignments_by_child[assignment.child_id].append(loaded)

    return {
        child.pk: {
            "active_periods": tuple(periods_by_turnus[child.turnus_id]),
            "focus_links": tuple(focuses_by_child[child.pk]),
            "active_events": tuple(events_by_turnus[child.turnus_id]),
            "assignments": tuple(assignments_by_child[child.pk]),
        }
        for child in children
    }


class Command(BaseCommand):
    help = "Check whether current child state fits the kid-edit audit schema."

    def add_arguments(self, parser):
        parser.add_argument("--turnus-id", type=int)

    def handle(self, *args, **options):
        turnus_id = options.get("turnus_id")
        if turnus_id is not None:
            if (
                turnus_id <= 0
                or not Turnus.objects.filter(pk=turnus_id).exists()
            ):
                raise CommandError("Candidate Turnus is unavailable.")
        queryset = Kinder.objects.all().order_by("pk")
        if turnus_id is not None:
            queryset = queryset.filter(turnus_id=turnus_id)
        children = list(queryset)
        inputs_by_child = _loaded_inputs(children)

        supported = 0
        unsupported = 0
        total_bytes = 0
        max_bytes = 0
        for child_ordinal, child in enumerate(children, start=1):
            try:
                snapshot = serialize_kid_edit_snapshot(
                    child=child,
                    **inputs_by_child[child.pk],
                )
            except (ValidationError, TypeError, ValueError, AttributeError):
                unsupported += 1
                self.stdout.write(
                    f"child_ordinal={child_ordinal} path=$ bytes=0"
                )
                continue

            candidate = {
                "schema": "budo.kid-edit",
                "version": 1,
                "result": "updated",
                "changed_paths": ["first_name"],
                "before": snapshot,
                "after": snapshot,
            }
            size = _encoded_size(candidate)
            total_bytes += size
            max_bytes = max(max_bytes, size)
            if size > MAX_KID_EDIT_AUDIT_BYTES:
                unsupported += 1
                self.stdout.write(
                    f"child_ordinal={child_ordinal} path=$ bytes={size}"
                )
                continue
            try:
                build_kid_edit_audit_details(
                    snapshot,
                    snapshot,
                    ["first_name"],
                )
            except ValidationError:
                unsupported += 1
                path = _unsupported_snapshot_path(snapshot)
                self.stdout.write(
                    f"child_ordinal={child_ordinal} path={path} bytes={size}"
                )
                continue
            supported += 1

        self.stdout.write(
            " ".join(
                (
                    f"checked={len(children)}",
                    f"supported={supported}",
                    f"unsupported={unsupported}",
                    f"total_bytes={total_bytes}",
                    f"max_bytes={max_bytes}",
                    f"limit_bytes={MAX_KID_EDIT_AUDIT_BYTES}",
                )
            )
        )
        if unsupported:
            raise CommandError("Unsupported kid-edit audit payloads found.")
