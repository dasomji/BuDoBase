"""Query-free serialization of caller-loaded kid-edit aggregate state."""

from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError

from budo_app.kid_edit_audit import validate_kid_edit_details
from budo_app.kid_edit_contracts import FIELD_CONTRACTS


@dataclass(frozen=True, repr=False)
class LoadedKidEditPeriod:
    period_id: int
    code: str
    label: str
    start: date
    duration_days: int

    def __repr__(self):
        return f"LoadedKidEditPeriod(period_id={self.period_id!r}, <redacted>)"


@dataclass(frozen=True, repr=False)
class LoadedKidEditFocusLink:
    period_id: int
    focus_id: int
    label: str

    def __repr__(self):
        return (
            "LoadedKidEditFocusLink("
            f"period_id={self.period_id!r}, focus_id={self.focus_id!r}, "
            "<redacted>)"
        )


@dataclass(frozen=True, repr=False)
class LoadedKidEditEvent:
    event_id: int
    display_number: int
    label: str
    revision: int

    def __repr__(self):
        return f"LoadedKidEditEvent(event_id={self.event_id!r}, <redacted>)"


@dataclass(frozen=True, repr=False)
class LoadedKidEditAssignment:
    event_id: int
    version: int
    kind: str
    station_id: int | None = None
    station_label: str | None = None
    station_event_id: int | None = None

    def __repr__(self):
        return (
            "LoadedKidEditAssignment("
            f"event_id={self.event_id!r}, kind={self.kind!r}, <redacted>)"
        )


def _plain_storage_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if value is None or type(value) in {str, int, bool}:
        return value
    raise ValidationError({"details": "Invalid loaded kid-edit field value."})


def _assignment_target(assignment, event_id):
    if assignment is None:
        return 0, {"kind": "unassigned"}
    if assignment.kind == "excused":
        if any(
            value is not None
            for value in (
                assignment.station_id,
                assignment.station_label,
                assignment.station_event_id,
            )
        ):
            raise ValidationError({"details": "Invalid loaded assignment."})
        return assignment.version, {"kind": "excused"}
    if assignment.kind == "station":
        if (
            assignment.station_event_id != event_id
            or assignment.station_id is None
            or type(assignment.station_label) is not str
        ):
            raise ValidationError({"details": "Invalid loaded assignment."})
        return assignment.version, {
            "kind": "station",
            "station_id": assignment.station_id,
            "station_label": assignment.station_label,
        }
    raise ValidationError({"details": "Invalid loaded assignment."})


def serialize_kid_edit_snapshot(
    *,
    child,
    active_periods,
    focus_links,
    active_events,
    assignments,
):
    """Serialize only the explicitly supplied, already-loaded aggregate state."""
    periods = tuple(active_periods)
    period_ids = {period.period_id for period in periods}
    focuses_by_period = {period_id: [] for period_id in period_ids}
    for focus in focus_links:
        if focus.period_id in period_ids:
            focuses_by_period[focus.period_id].append(focus)
    for focuses in focuses_by_period.values():
        focuses.sort(key=lambda focus: (focus.label.casefold(), focus.focus_id))

    events = tuple(active_events)
    event_ids = {event.event_id for event in events}
    assignments_by_event = {}
    for assignment in assignments:
        if assignment.event_id not in event_ids:
            continue
        if assignment.event_id in assignments_by_event:
            raise ValidationError({"details": "Invalid loaded assignment."})
        assignments_by_event[assignment.event_id] = assignment

    fields = {
        field.api_name: _plain_storage_value(
            getattr(child, field.storage_name)
        )
        for field in FIELD_CONTRACTS
    }
    swp = [
        {
            "period_id": period.period_id,
            "period_code": period.code,
            "period_label": period.label,
            "start": period.start.isoformat(),
            "duration_days": period.duration_days,
            "focuses": [
                {"id": focus.focus_id, "label": focus.label}
                for focus in focuses_by_period[period.period_id]
            ],
        }
        for period in sorted(
            periods,
            key=lambda period: (period.start, period.period_id),
        )
    ]
    happy_cleaning = []
    for event in sorted(
        events,
        key=lambda event: (event.display_number, event.event_id),
    ):
        version, target = _assignment_target(
            assignments_by_event.get(event.event_id),
            event.event_id,
        )
        happy_cleaning.append(
            {
                "event_id": event.event_id,
                "display_number": event.display_number,
                "event_label": event.label,
                "event_revision": event.revision,
                "assignment_version": version,
                "target": target,
            }
        )
    return {
        "versions": {
            "edit": child.edit_version,
            "happy_cleaning_number": child.happy_cleaning_number_version,
        },
        "fields": fields,
        "happy_cleaning_number": child.happy_cleaning_number,
        "swp": swp,
        "happy_cleaning": happy_cleaning,
    }


def build_kid_edit_audit_details(before, after, changed_paths):
    """Build and validate one successful v1 kid-edit audit detail object."""
    return validate_kid_edit_details(
        {
            "schema": "budo.kid-edit",
            "version": 1,
            "result": "updated",
            "changed_paths": list(changed_paths),
            "before": before,
            "after": after,
        },
        expected_changed_paths=changed_paths,
    )
