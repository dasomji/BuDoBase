"""Race-safe application services for child numbers and assignments."""

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import F

from budo_app.audit import AuditEventData, record_rejected_attempt
from budo_app.happy_cleaning_assignment_publisher import (
    publish_assignment_invalidation_on_commit,
)
from budo_app.happy_cleaning_commands import (
    CommandError,
    audit_success,
    complete_command,
    replay_completed_command,
)
from budo_app.happy_cleaning_number_batch import (
    BATCH_NUMBER_ACTION,
    number_batch_projection,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Profil,
)
from budo_app.read_contracts.common import kid_full_name


NUMBER_COMMAND_ACTION = "happy_cleaning.child_number.change"


class AssignmentCommandError(CommandError):
    def __init__(self, code, *, projection=None, **kwargs):
        super().__init__(code, **kwargs)
        self.projection = projection or {}


class LockedMutationError(Exception):
    """Projection-free failure from a lock-assuming mutation seam."""

    def __init__(self, code, *, current_version=None):
        super().__init__(code)
        self.code = code
        self.current_version = current_version


@dataclass(frozen=True, slots=True)
class LockedChildNumberPlan:
    child_id: int
    turnus_id: int
    number: int | None
    previous_number: int | None
    expected_version: int
    changed: bool


@dataclass(frozen=True, slots=True)
class LockedAssignmentPlan:
    child_id: int
    turnus_id: int
    event_id: int
    source_assignment_id: int | None
    source_version: int
    source_target_kind: str
    source_station_id: int | None
    target_kind: str
    target_station_id: int | None
    changed: bool


def _lock_actor(context):
    Profil.objects.select_for_update().get(user_id=context.actor_id)


def _child_projection(child):
    return {
        "id": child.id,
        "full_name": kid_full_name(child.kid_vorname, child.kid_nachname),
        "number": child.happy_cleaning_number,
        "number_version": child.happy_cleaning_number_version,
    }


def _assignment_projection(assignment, child_id):
    if assignment is None:
        return {
            "child_id": child_id,
            "station": None,
            "version": None,
        }
    station = (
        {
            "id": "excused",
            "name": "Entschuldigt",
            "is_excused": True,
        }
        if assignment.is_excused
        else {
            "id": assignment.station_id,
            "name": assignment.station.name,
        }
    )
    return {
        "child_id": child_id,
        "station": station,
        "version": assignment.version,
    }


def _station_projection(station):
    assigned_count = station.assignments.count()
    return {
        "id": station.id,
        "name": station.name,
        "max_kids": station.max_kids,
        "assigned_count": assigned_count,
        "free_seats": max(station.max_kids - assigned_count, 0),
        "overbooked_count": max(assigned_count - station.max_kids, 0),
    }


def _event_for_context(context, event_id):
    event = HappyCleaning.objects.filter(
        pk=event_id,
        turnus_id=context.turnus.id,
    ).first()
    if event is None:
        raise AssignmentCommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details={"happy_cleaning_id": event_id},
        )
    return event


def _increment_event_revision(event):
    HappyCleaning.objects.filter(pk=event.pk).update(revision=F("revision") + 1)
    event.refresh_from_db(fields=("revision",))
    return event.revision


def _increment_turnus_event_revisions(turnus_id):
    return bump_locked_event_revisions_once(
        turnus_id=turnus_id,
        number_changed=True,
        assignment_event_ids=(),
    )


def _lock_affected_event_rows(
    *,
    turnus_id,
    number_changed,
    assignment_event_ids,
):
    assignment_event_ids = frozenset(assignment_event_ids)
    if not number_changed and not assignment_event_ids:
        return []

    events = HappyCleaning.objects.select_for_update().filter(
        turnus_id=turnus_id,
    )
    if not number_changed:
        events = events.filter(pk__in=assignment_event_ids)
    return list(events.order_by("pk"))


def bump_locked_event_revisions_once(
    *,
    turnus_id,
    number_changed,
    assignment_event_ids,
):
    """Lock and bump the caller's affected Turnus events exactly once."""
    events = _lock_affected_event_rows(
        turnus_id=turnus_id,
        number_changed=number_changed,
        assignment_event_ids=assignment_event_ids,
    )

    revisions = []
    for event in events:
        event.revision += 1
        event.save(update_fields=("revision",))
        revisions.append((event.id, event.revision))
    return revisions


def _duplicate_number_projection(turnus_id, requested_number):
    first = max(1, requested_number - 3)
    last = requested_number + 3
    occupied = {
        child.happy_cleaning_number: child
        for child in Kinder.objects.filter(
            turnus_id=turnus_id,
            happy_cleaning_number__range=(first, last),
        ).only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "happy_cleaning_number",
        )
    }
    return [
        {
            "number": number,
            "free": number not in occupied,
            "child": (
                None
                if number not in occupied
                else {
                    "id": occupied[number].id,
                    "display_name": kid_full_name(
                        occupied[number].kid_vorname,
                        occupied[number].kid_nachname,
                    ),
                }
            ),
        }
        for number in range(first, last + 1)
    ]


def _conflict(code, *, projection, outcome, details, current_version=None):
    raise AssignmentCommandError(
        code,
        status=409,
        projection=projection,
        current_version=current_version,
        audit_outcome=outcome,
        details=details,
    )


def plan_locked_child_number(*, child, turnus_id, number, expected_version):
    """Validate a number change against child state locked by the caller."""
    if child.turnus_id != turnus_id:
        raise LockedMutationError("not_found")
    if child.happy_cleaning_number_version != expected_version:
        raise LockedMutationError(
            "stale",
            current_version=child.happy_cleaning_number_version,
        )
    if number is not None and (
        isinstance(number, bool)
        or not isinstance(number, int)
        or number <= 0
    ):
        raise LockedMutationError("validation_error")

    changed = child.happy_cleaning_number != number
    if changed and number is not None and Kinder.objects.filter(
        turnus_id=turnus_id,
        happy_cleaning_number=number,
    ).exclude(pk=child.id).exists():
        raise LockedMutationError(
            "duplicate_number",
            current_version=child.happy_cleaning_number_version,
        )

    return LockedChildNumberPlan(
        child_id=child.id,
        turnus_id=turnus_id,
        number=number,
        previous_number=child.happy_cleaning_number,
        expected_version=expected_version,
        changed=changed,
    )


def apply_locked_child_number(*, child, plan):
    """Apply a number change to a child locked by the caller.

    The caller owns the surrounding transaction and any command-level side
    effects such as event revisions, audit, idempotency, and publication.
    """
    if not isinstance(plan, LockedChildNumberPlan):
        raise LockedMutationError("plan_mismatch")
    if child.id != plan.child_id or child.turnus_id != plan.turnus_id:
        raise LockedMutationError("plan_mismatch")
    if (
        child.happy_cleaning_number_version != plan.expected_version
        or child.happy_cleaning_number != plan.previous_number
    ):
        raise LockedMutationError(
            "stale",
            current_version=child.happy_cleaning_number_version,
        )
    if plan.number is not None and (
        isinstance(plan.number, bool)
        or not isinstance(plan.number, int)
        or plan.number <= 0
    ):
        raise LockedMutationError("validation_error")
    if plan.changed != (plan.previous_number != plan.number):
        raise LockedMutationError("plan_mismatch")
    if not plan.changed:
        return False

    previous_number = child.happy_cleaning_number
    previous_version = child.happy_cleaning_number_version
    child.happy_cleaning_number = plan.number
    child.happy_cleaning_number_version += 1
    try:
        child.save(update_fields=(
            "happy_cleaning_number",
            "happy_cleaning_number_version",
        ))
    except IntegrityError:
        child.happy_cleaning_number = previous_number
        child.happy_cleaning_number_version = previous_version
        raise
    return True


def _raise_number_command_error(
    error,
    *,
    child,
    turnus_id,
    number,
    expected_version,
):
    if error.code == "not_found":
        raise AssignmentCommandError(
            "not_found",
            status=404,
            audit_outcome="forbidden",
            details={"child_id": child.id},
        ) from error
    if error.code == "stale":
        _conflict(
            "stale",
            projection={"child": _child_projection(child)},
            outcome="stale",
            current_version=error.current_version,
            details={
                "child_id": child.id,
                "expected_version": expected_version,
                "current_version": error.current_version,
            },
        )
    if error.code == "validation_error":
        raise AssignmentCommandError(
            "validation_error",
            errors={"number": ["A positive integer or null is required."]},
        ) from error
    if error.code == "duplicate_number":
        _conflict(
            "duplicate_number",
            projection={
                "child": _child_projection(child),
                "neighborhood": _duplicate_number_projection(turnus_id, number),
            },
            outcome="duplicate_number",
            details={
                "child_id": child.id,
                "new_number": number,
                "expected_version": expected_version,
                "current_version": error.current_version,
            },
        )
    raise error


def set_child_number(context, child_id, number, expected_version):
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, NUMBER_COMMAND_ACTION)
        if replay is not None:
            return replay, True
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .only(
                "id",
                "turnus_id",
                "kid_vorname",
                "kid_nachname",
                "happy_cleaning_number",
                "happy_cleaning_number_version",
            )
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"child_id": child_id},
            )
        try:
            plan = plan_locked_child_number(
                child=child,
                turnus_id=context.turnus.id,
                number=number,
                expected_version=expected_version,
            )
        except LockedMutationError as error:
            _raise_number_command_error(
                error,
                child=child,
                turnus_id=context.turnus.id,
                number=number,
                expected_version=expected_version,
            )
        previous = child.happy_cleaning_number
        event_revisions = []
        if plan.changed:
            try:
                with transaction.atomic():
                    apply_locked_child_number(child=child, plan=plan)
            except LockedMutationError as error:
                _raise_number_command_error(
                    error,
                    child=child,
                    turnus_id=context.turnus.id,
                    number=number,
                    expected_version=expected_version,
                )
            except IntegrityError:
                neighborhood = _duplicate_number_projection(
                    context.turnus.id,
                    number,
                )
                _conflict(
                    "duplicate_number",
                    projection={
                        "child": _child_projection(
                            Kinder.objects.only(
                                "id",
                                "kid_vorname",
                                "kid_nachname",
                                "happy_cleaning_number",
                                "happy_cleaning_number_version",
                            ).get(pk=child.id)
                        ),
                        "neighborhood": neighborhood,
                    },
                    outcome="duplicate_number",
                    details={
                        "child_id": child.id,
                        "new_number": number,
                        "expected_version": expected_version,
                        "current_version": expected_version,
                    },
                )
            event_revisions = _increment_turnus_event_revisions(context.turnus.id)
        audit_action = (
            "happy_cleaning.child_number.set"
            if previous is None and number is not None
            else "happy_cleaning.child_number.change"
        )
        audit_success(
            context,
            action=audit_action,
            resource_type="child",
            resource_id=child.id,
            resource_label=kid_full_name(child.kid_vorname, child.kid_nachname),
            details={
                "child_id": child.id,
                "previous_number": previous,
                "new_number": number,
                "expected_version": expected_version,
                "current_version": child.happy_cleaning_number_version,
            },
        )
        response = complete_command(context, NUMBER_COMMAND_ACTION, {
            "ok": True,
            "child": _child_projection(child),
        })
        for happy_cleaning_id, revision in event_revisions:
            publish_assignment_invalidation_on_commit({
                "kind": "child_number",
                "happy_cleaning_id": happy_cleaning_id,
                "revision": revision,
                "request_id": context.request_id,
            })
        return response, False


def _locked_assignment_target(assignment):
    if assignment is None:
        return "unassigned", None
    if (
        assignment.target_kind == HappyCleaningAssignment.TargetKind.EXCUSED
        and assignment.station_id is None
    ):
        return "excused", None
    if (
        assignment.target_kind == HappyCleaningAssignment.TargetKind.STATION
        and assignment.station_id is not None
    ):
        return "station", assignment.station_id
    raise LockedMutationError("validation_error")


def _validate_assignment_target_shape(*, target_kind, station):
    if target_kind == "station":
        if station is None:
            raise LockedMutationError("validation_error")
        return station.id
    if target_kind in {"excused", "unassigned"}:
        if station is not None:
            raise LockedMutationError("validation_error")
        return None
    raise LockedMutationError("validation_error")


def plan_locked_assignment_change(
    *,
    child,
    event,
    current_assignment,
    target_kind,
    station=None,
    expected_version,
):
    """Validate an assignment change against caller-locked domain state."""
    if child.turnus_id != event.turnus_id:
        raise LockedMutationError("not_found")
    if current_assignment is not None and (
        current_assignment.child_id != child.id
        or current_assignment.happy_cleaning_id != event.id
    ):
        raise LockedMutationError("not_found")

    current_version = (
        0 if current_assignment is None else current_assignment.version
    )
    if current_version != expected_version:
        raise LockedMutationError(
            "stale",
            current_version=current_version,
        )

    target_station_id = _validate_assignment_target_shape(
        target_kind=target_kind,
        station=station,
    )
    if station is not None and station.happy_cleaning_id != event.id:
        raise LockedMutationError("not_found")

    source_target_kind, source_station_id = _locked_assignment_target(
        current_assignment,
    )
    changed = (
        source_target_kind != target_kind
        or source_station_id != target_station_id
    )
    if target_kind == "station" and child.happy_cleaning_number is None:
        raise LockedMutationError("number_required")
    if (
        changed
        and target_kind == "station"
        and station.assignments.count() >= station.max_kids
    ):
        raise LockedMutationError("station_full")

    return LockedAssignmentPlan(
        child_id=child.id,
        turnus_id=child.turnus_id,
        event_id=event.id,
        source_assignment_id=(
            None if current_assignment is None else current_assignment.id
        ),
        source_version=current_version,
        source_target_kind=source_target_kind,
        source_station_id=source_station_id,
        target_kind=target_kind,
        target_station_id=target_station_id,
        changed=changed,
    )


def _validate_assignment_plan_binding(
    *,
    child,
    event,
    current_assignment,
    plan,
):
    if not isinstance(plan, LockedAssignmentPlan):
        raise LockedMutationError("plan_mismatch")
    if (
        child.id != plan.child_id
        or child.turnus_id != plan.turnus_id
        or event.id != plan.event_id
        or event.turnus_id != plan.turnus_id
    ):
        raise LockedMutationError("plan_mismatch")

    current_id = None if current_assignment is None else current_assignment.id
    current_version = (
        0 if current_assignment is None else current_assignment.version
    )
    if current_id != plan.source_assignment_id:
        raise LockedMutationError(
            "stale",
            current_version=current_version,
        )
    if current_assignment is not None and (
        current_assignment.child_id != child.id
        or current_assignment.happy_cleaning_id != event.id
    ):
        raise LockedMutationError("plan_mismatch")
    if current_version != plan.source_version:
        raise LockedMutationError(
            "stale",
            current_version=current_version,
        )

    try:
        source_target = _locked_assignment_target(current_assignment)
    except LockedMutationError as error:
        raise LockedMutationError(
            "stale",
            current_version=current_version,
        ) from error
    if source_target != (
        plan.source_target_kind,
        plan.source_station_id,
    ):
        raise LockedMutationError(
            "stale",
            current_version=current_version,
        )

    valid_target = (
        (
            plan.target_kind == "station"
            and isinstance(plan.target_station_id, int)
            and not isinstance(plan.target_station_id, bool)
            and plan.target_station_id > 0
        )
        or (
            plan.target_kind in {"excused", "unassigned"}
            and plan.target_station_id is None
        )
    )
    if not valid_target:
        raise LockedMutationError("plan_mismatch")
    changed = (
        plan.source_target_kind != plan.target_kind
        or plan.source_station_id != plan.target_station_id
    )
    if plan.changed != changed:
        raise LockedMutationError("plan_mismatch")


def apply_locked_assignment_change(
    *,
    child,
    event,
    current_assignment,
    plan,
    event_revision,
    target_station,
):
    """Apply a validated assignment plan using the caller's event revision."""
    _validate_assignment_plan_binding(
        child=child,
        event=event,
        current_assignment=current_assignment,
        plan=plan,
    )
    if (
        isinstance(event_revision, bool)
        or not isinstance(event_revision, int)
        or event_revision <= 0
    ):
        raise LockedMutationError("validation_error")
    if event_revision != event.revision:
        raise LockedMutationError(
            "stale",
            current_version=event.revision,
        )

    if plan.target_kind == "station":
        if (
            target_station is None
            or target_station.id != plan.target_station_id
            or target_station.happy_cleaning_id != event.id
        ):
            raise LockedMutationError("plan_mismatch")
        if child.happy_cleaning_number is None:
            raise LockedMutationError("number_required")
        if (
            plan.changed
            and target_station.assignments.count() >= target_station.max_kids
        ):
            raise LockedMutationError("station_full")
    elif target_station is not None:
        raise LockedMutationError("plan_mismatch")
    if not plan.changed:
        return False

    if plan.target_kind == "unassigned":
        current_assignment.delete()
        return True

    if current_assignment is None:
        HappyCleaningAssignment.objects.create(
            happy_cleaning=event,
            child=child,
            station=target_station,
            target_kind=plan.target_kind,
            version=event_revision,
        )
        return True

    current_assignment.station = target_station
    current_assignment.target_kind = plan.target_kind
    current_assignment.version = event_revision
    current_assignment.save(update_fields=(
        "station",
        "target_kind",
        "version",
    ))
    return True


def _assignment_for_update(event_id, child_id):
    return (
        HappyCleaningAssignment.objects.select_for_update(of=("self",))
        .select_related("station")
        .filter(happy_cleaning_id=event_id, child_id=child_id)
        .first()
    )


def assign_child(context, event_id, child_id, station_id):
    action = "happy_cleaning.assignment.assign"
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        station = (
            HappyCleaningStation.objects.select_for_update()
            .filter(pk=station_id, happy_cleaning_id=event.id)
            .first()
        )
        if station is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "station_id": station_id},
            )
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "child_id": child_id},
            )
        current = _assignment_for_update(event.id, child.id)
        if current is not None:
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(current, child.id)},
                outcome="stale",
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child.id,
                    "current_version": current.version,
                },
                current_version=current.version,
            )
        if child.happy_cleaning_number is None:
            _conflict(
                "number_required",
                projection={"child": _child_projection(child)},
                outcome=None,
                details={},
            )
        if station.assignments.count() >= station.max_kids:
            _conflict(
                "station_full",
                projection={"station": _station_projection(station)},
                outcome="station_full",
                details={
                    "happy_cleaning_id": event.id,
                    "station_id": station.id,
                    "child_id": child.id,
                },
            )
        revision = _increment_event_revision(event)
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=event,
            station=station,
            child=child,
            version=revision,
        )
        station.refresh_from_db(fields=("has_ever_had_assignment",))
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning_assignment",
            resource_id=assignment.id,
            resource_label=kid_full_name(child.kid_vorname, child.kid_nachname),
            details={
                "happy_cleaning_id": event.id,
                "child_id": child.id,
                "previous_station_id": None,
                "new_station_id": station.id,
                "current_version": assignment.version,
            },
        )
        response = complete_command(context, action, {
            "ok": True,
            "assignment": _assignment_projection(assignment, child.id),
            "station": _station_projection(station),
            "event_revision": revision,
        })
        publish_assignment_invalidation_on_commit({
            "kind": "assignment",
            "happy_cleaning_id": event.id,
            "revision": revision,
            "request_id": context.request_id,
        })
        return response, False


def assign_excused_child(context, event_id, child_id):
    action = "happy_cleaning.assignment.excuse"
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "child_id": child_id},
            )
        current = _assignment_for_update(event.id, child.id)
        if current is not None:
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(current, child.id)},
                outcome="stale",
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child.id,
                    "current_version": current.version,
                },
                current_version=current.version,
            )
        revision = _increment_event_revision(event)
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=event,
            station=None,
            target_kind=HappyCleaningAssignment.TargetKind.EXCUSED,
            child=child,
            version=revision,
        )
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning_assignment",
            resource_id=assignment.id,
            resource_label=kid_full_name(child.kid_vorname, child.kid_nachname),
            details={
                "happy_cleaning_id": event.id,
                "child_id": child.id,
                "previous_station_id": None,
                "new_station_id": "excused",
                "current_version": assignment.version,
            },
        )
        response = complete_command(context, action, {
            "ok": True,
            "assignment": _assignment_projection(assignment, child.id),
            "event_revision": revision,
        })
        publish_assignment_invalidation_on_commit({
            "kind": "assignment",
            "happy_cleaning_id": event.id,
            "revision": revision,
            "request_id": context.request_id,
        })
        return response, False


def _current_assignment_before_station_locks(event, child_id):
    return (
        HappyCleaningAssignment.objects.filter(
            happy_cleaning_id=event.id,
            child_id=child_id,
        )
        .only("id", "station_id")
        .first()
    )


def move_child(context, event_id, child_id, station_id, expected_version):
    action = "happy_cleaning.assignment.move"
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        observed = _current_assignment_before_station_locks(event, child_id)
        if observed is None:
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(None, child_id)},
                outcome="stale",
                current_version=0,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child_id,
                    "expected_version": expected_version,
                    "current_version": 0,
                },
            )
        stations = list(
            HappyCleaningStation.objects.select_for_update()
            .filter(
                pk__in=(observed.station_id, station_id),
                happy_cleaning_id=event.id,
            )
            .order_by("pk")
        )
        stations_by_id = {station.id: station for station in stations}
        target = stations_by_id.get(station_id)
        if target is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "station_id": station_id},
            )
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "child_id": child_id},
            )
        assignment = _assignment_for_update(event.id, child.id)
        if assignment is None or assignment.version != expected_version:
            current_version = assignment.version if assignment else 0
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(assignment, child.id)},
                outcome="stale",
                current_version=current_version,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child.id,
                    "expected_version": expected_version,
                    "current_version": current_version,
                },
            )
        previous_station_id = (
            "excused" if assignment.is_excused else assignment.station_id
        )
        target_changed = assignment.is_excused or assignment.station_id != target.id
        if child.happy_cleaning_number is None:
            _conflict(
                "number_required",
                projection={"child": _child_projection(child)},
                outcome=None,
                details={},
            )
        if target_changed:
            if target.assignments.count() >= target.max_kids:
                _conflict(
                    "station_full",
                    projection={
                        "assignment": _assignment_projection(assignment, child.id),
                        "station": _station_projection(target),
                    },
                    outcome="station_full",
                    details={
                        "happy_cleaning_id": event.id,
                        "station_id": target.id,
                        "child_id": child.id,
                        "previous_station_id": previous_station_id,
                        "expected_version": expected_version,
                        "current_version": assignment.version,
                    },
                )
            revision = _increment_event_revision(event)
            assignment.station = target
            assignment.target_kind = HappyCleaningAssignment.TargetKind.STATION
            assignment.version = revision
            assignment.save(update_fields=("station", "target_kind", "version"))
        else:
            revision = event.revision
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning_assignment",
            resource_id=assignment.id,
            resource_label=kid_full_name(child.kid_vorname, child.kid_nachname),
            details={
                "happy_cleaning_id": event.id,
                "child_id": child.id,
                "previous_station_id": previous_station_id,
                "new_station_id": target.id,
                "expected_version": expected_version,
                "current_version": assignment.version,
            },
        )
        response = complete_command(context, action, {
            "ok": True,
            "assignment": _assignment_projection(assignment, child.id),
            "station": _station_projection(target),
            "event_revision": revision,
        })
        if target_changed:
            publish_assignment_invalidation_on_commit({
                "kind": "assignment",
                "happy_cleaning_id": event.id,
                "revision": revision,
                "request_id": context.request_id,
            })
        return response, False


def move_child_to_excused(context, event_id, child_id, expected_version):
    action = "happy_cleaning.assignment.move_to_excused"
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        observed = _current_assignment_before_station_locks(event, child_id)
        if observed is None:
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(None, child_id)},
                outcome="stale",
                current_version=0,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child_id,
                    "expected_version": expected_version,
                    "current_version": 0,
                },
            )
        if observed.station_id is not None:
            HappyCleaningStation.objects.select_for_update().get(
                pk=observed.station_id,
                happy_cleaning_id=event.id,
            )
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "child_id": child_id},
            )
        assignment = _assignment_for_update(event.id, child.id)
        if assignment is None or assignment.version != expected_version:
            current_version = assignment.version if assignment else 0
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(assignment, child.id)},
                outcome="stale",
                current_version=current_version,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child.id,
                    "expected_version": expected_version,
                    "current_version": current_version,
                },
            )
        previous_station_id = (
            "excused" if assignment.is_excused else assignment.station_id
        )
        if not assignment.is_excused:
            revision = _increment_event_revision(event)
            assignment.station = None
            assignment.target_kind = HappyCleaningAssignment.TargetKind.EXCUSED
            assignment.version = revision
            assignment.save(update_fields=("station", "target_kind", "version"))
        else:
            revision = event.revision
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning_assignment",
            resource_id=assignment.id,
            resource_label=kid_full_name(child.kid_vorname, child.kid_nachname),
            details={
                "happy_cleaning_id": event.id,
                "child_id": child.id,
                "previous_station_id": previous_station_id,
                "new_station_id": "excused",
                "expected_version": expected_version,
                "current_version": assignment.version,
            },
        )
        response = complete_command(context, action, {
            "ok": True,
            "assignment": _assignment_projection(assignment, child.id),
            "event_revision": revision,
        })
        if previous_station_id != "excused":
            publish_assignment_invalidation_on_commit({
                "kind": "assignment",
                "happy_cleaning_id": event.id,
                "revision": revision,
                "request_id": context.request_id,
            })
        return response, False


def remove_child(context, event_id, child_id, expected_version):
    action = "happy_cleaning.assignment.remove"
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        observed = _current_assignment_before_station_locks(event, child_id)
        if observed is None:
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(None, child_id)},
                outcome="stale",
                current_version=0,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child_id,
                    "expected_version": expected_version,
                    "current_version": 0,
                },
            )
        if observed.station_id is not None:
            HappyCleaningStation.objects.select_for_update().get(
                pk=observed.station_id,
                happy_cleaning_id=event.id,
            )
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=context.turnus.id)
            .first()
        )
        if child is None:
            raise AssignmentCommandError(
                "not_found",
                status=404,
                audit_outcome="forbidden",
                details={"happy_cleaning_id": event.id, "child_id": child_id},
            )
        assignment = _assignment_for_update(event.id, child.id)
        if assignment is None or assignment.version != expected_version:
            current_version = assignment.version if assignment else 0
            _conflict(
                "stale",
                projection={"assignment": _assignment_projection(assignment, child.id)},
                outcome="stale",
                current_version=current_version,
                details={
                    "happy_cleaning_id": event.id,
                    "child_id": child.id,
                    "expected_version": expected_version,
                    "current_version": current_version,
                },
            )
        assignment_id = assignment.id
        previous_station_id = (
            "excused" if assignment.is_excused else assignment.station_id
        )
        label = kid_full_name(child.kid_vorname, child.kid_nachname)
        assignment.delete()
        revision = _increment_event_revision(event)
        audit_success(
            context,
            action=action,
            resource_type="happy_cleaning_assignment",
            resource_id=assignment_id,
            resource_label=label,
            details={
                "happy_cleaning_id": event.id,
                "child_id": child.id,
                "previous_station_id": previous_station_id,
                "new_station_id": None,
                "expected_version": expected_version,
                "current_version": revision,
            },
        )
        response = complete_command(context, action, {
            "ok": True,
            "assignment": _assignment_projection(None, child.id),
            "event_revision": revision,
        })
        publish_assignment_invalidation_on_commit({
            "kind": "assignment",
            "happy_cleaning_id": event.id,
            "revision": revision,
            "request_id": context.request_id,
        })
        return response, False


def assign_missing_numbers(context, event_id, requested_assignments):
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, BATCH_NUMBER_ACTION)
        if replay is not None:
            return replay, True
        event = _event_for_context(context, event_id)
        children = list(
            Kinder.objects.select_for_update()
            .filter(turnus_id=context.turnus.id)
            .only(
                "id",
                "kid_vorname",
                "kid_nachname",
                "happy_cleaning_number",
                "happy_cleaning_number_version",
                "anwesend",
            )
            .order_by("kid_vorname", "kid_nachname", "id")
        )
        locked_events = _lock_affected_event_rows(
            turnus_id=context.turnus.id,
            number_changed=True,
            assignment_event_ids=(),
        )
        first_event = next(
            (
                locked_event
                for locked_event in locked_events
                if locked_event.display_number == 1
            ),
            None,
        )
        present_ids = {
            child.id for child in children if child.anwesend is True
        }
        assigned_ids = set()
        if first_event is not None:
            assigned_ids = set(
                HappyCleaningAssignment.objects.select_for_update()
                .filter(
                    happy_cleaning_id=first_event.id,
                    child_id__in=present_ids,
                    child__turnus_id=context.turnus.id,
                )
                .values_list("child_id", flat=True)
            )
        unlocked = (
            first_event is not None
            and present_ids.issubset(assigned_ids)
        )
        projection = number_batch_projection(children, unlocked=unlocked)
        if not unlocked:
            _conflict(
                "batch_locked",
                projection={"number_batch": projection},
                outcome=None,
                details={"happy_cleaning_id": event.id},
            )
        if not projection["available"]:
            _conflict(
                "nothing_to_assign",
                projection={"number_batch": projection},
                outcome=None,
                details={"happy_cleaning_id": event.id},
            )
        expected = [
            {
                "child_id": item["id"],
                "number": item["number"],
                "expected_version": item["expected_version"],
            }
            for item in projection["children"]
        ]
        if requested_assignments != expected:
            _conflict(
                "stale",
                projection={"number_batch": projection},
                outcome="stale",
                details={"happy_cleaning_id": event.id},
            )

        children_by_id = {child.id: child for child in children}
        changed = []
        try:
            with transaction.atomic():
                for item in expected:
                    child = children_by_id[item["child_id"]]
                    child.happy_cleaning_number = item["number"]
                    child.happy_cleaning_number_version += 1
                    child.save(update_fields=(
                        "happy_cleaning_number",
                        "happy_cleaning_number_version",
                    ))
                    changed.append(child)
        except IntegrityError:
            for child in children:
                child.refresh_from_db(fields=(
                    "happy_cleaning_number",
                    "happy_cleaning_number_version",
                    "anwesend",
                ))
            current = number_batch_projection(children, unlocked=True)
            _conflict(
                "stale",
                projection={"number_batch": current},
                outcome="stale",
                details={"happy_cleaning_id": event.id},
            )

        event_revisions = _increment_turnus_event_revisions(context.turnus.id)
        audit_success(
            context,
            action=BATCH_NUMBER_ACTION,
            resource_type="happy_cleaning",
            resource_id=event.id,
            resource_label=f"Happy Cleaning {event.display_number}",
            details={
                "happy_cleaning_id": event.id,
                "result_count": len(expected),
            },
        )
        response = complete_command(context, BATCH_NUMBER_ACTION, {
            "ok": True,
            "children": [_child_projection(child) for child in changed],
        })
        for happy_cleaning_id, revision in event_revisions:
            publish_assignment_invalidation_on_commit({
                "kind": "child_number",
                "happy_cleaning_id": happy_cleaning_id,
                "revision": revision,
                "request_id": context.request_id,
            })
        return response, False


def rejection_response(context, action, error):
    """Consume a rejected request ID once and return a replayable projection."""
    with transaction.atomic():
        _lock_actor(context)
        replay = replay_completed_command(context, action)
        if replay is not None:
            return replay, True
        payload = {"ok": False, "code": error.code, **error.projection}
        if error.current_version is not None:
            payload["current_version"] = error.current_version
        response = complete_command(context, action, payload)
    if error.audit_outcome in {
        "forbidden",
        "stale",
        "station_full",
        "duplicate_number",
    }:
        record_rejected_attempt(AuditEventData(
            turnus=context.turnus,
            actor_id=context.actor_id,
            actor_label=context.actor_label,
            action=action,
            outcome=error.audit_outcome,
            resource_type="happy_cleaning_command",
            resource_id=str(error.details.get("child_id", "hidden")),
            resource_label="Happy Cleaning command",
            request_id=context.request_id,
            client_ip=context.client_ip,
            user_agent=context.user_agent,
            details=error.details,
        ))
    return response, False
