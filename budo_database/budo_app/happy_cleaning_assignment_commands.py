"""Race-safe application services for child numbers and assignments."""

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
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Profil,
    Turnus,
)
from budo_app.read_contracts.common import kid_full_name


NUMBER_COMMAND_ACTION = "happy_cleaning.child_number.change"


class AssignmentCommandError(CommandError):
    def __init__(self, code, *, projection=None, **kwargs):
        super().__init__(code, **kwargs)
        self.projection = projection or {}


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
    return {
        "child_id": child_id,
        "station": {
            "id": assignment.station_id,
            "name": assignment.station.name,
        },
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
    HappyCleaning.objects.filter(turnus_id=turnus_id).update(
        revision=F("revision") + 1,
    )
    return list(
        HappyCleaning.objects.filter(turnus_id=turnus_id)
        .values_list("id", "revision")
        .order_by("id")
    )


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
        if child.happy_cleaning_number_version != expected_version:
            _conflict(
                "stale",
                projection={"child": _child_projection(child)},
                outcome="stale",
                current_version=child.happy_cleaning_number_version,
                details={
                    "child_id": child.id,
                    "expected_version": expected_version,
                    "current_version": child.happy_cleaning_number_version,
                },
            )
        previous = child.happy_cleaning_number
        event_revisions = []
        if previous != number:
            child.happy_cleaning_number = number
            child.happy_cleaning_number_version += 1
            try:
                with transaction.atomic():
                    child.save(update_fields=(
                        "happy_cleaning_number",
                        "happy_cleaning_number_version",
                    ))
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


def _assignment_for_update(event_id, child_id):
    return (
        HappyCleaningAssignment.objects.select_for_update()
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
        previous_station_id = assignment.station_id
        if previous_station_id != target.id:
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
            assignment.version = revision
            assignment.save(update_fields=("station", "version"))
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
        if previous_station_id != target.id:
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
        previous_station_id = assignment.station_id
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
