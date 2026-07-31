"""Atomic orchestration for the complete kid-edit aggregate."""

from dataclasses import dataclass

from django.db import transaction

from budo_app.audit import AuditEventData, record_audit_event
from budo_app import happy_cleaning_assignment_commands
from budo_app import kid_edit_writes
from budo_app.happy_cleaning_assignment_commands import (
    LockedMutationError,
    bump_locked_event_revisions_once,
    plan_locked_assignment_change,
    plan_locked_child_number,
)
from budo_app.happy_cleaning_assignment_publisher import (
    publish_assignment_invalidation_on_commit,
)
from budo_app.kid_edit_audit_snapshot import (
    LoadedKidEditAssignment,
    LoadedKidEditEvent,
    LoadedKidEditFocusLink,
    LoadedKidEditPeriod,
    build_kid_edit_audit_details,
    serialize_kid_edit_snapshot,
)
from budo_app.kid_edit_contracts import (
    FIELD_CONTRACTS,
    KidEditCurrentHappyCleaningEvent,
    KidEditCurrentHappyCleaningTarget,
    KidEditCurrentState,
    KidEditCurrentSwpPeriod,
    KidEditValidationError,
    validate_kid_edit_command,
)
from budo_app.kid_edit_fingerprint import (
    sign_kid_edit_request,
    verify_kid_edit_request_fingerprint,
)
from budo_app.kid_edit_writes import (
    _VersionedChildWrite,
    plan_locked_swp_change,
)
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
    Profil,
    Turnus,
)


ACTION = "kid.edit"


@dataclass(frozen=True)
class KidEditCommandError(Exception):
    status: int
    payload: dict


def _plain_errors(errors):
    return {
        name: [
            {"code": item.code, "message": item.message}
            for item in items
        ]
        for name, items in errors.items()
    }


def validation_error_response(error):
    payload = {
        "ok": False,
        "code": error.code,
        "errors": _plain_errors(error.errors),
        "replayed": False,
    }
    if isinstance(error, KidEditValidationError):
        payload.update({
            "current_versions": {
                "edit": error.current_versions["edit"],
                "happy_cleaning_number": error.current_versions[
                    "happy_cleaning_number"
                ],
                "happy_cleaning": dict(error.current_versions[
                    "happy_cleaning"
                ]),
            },
            "reload_required": error.status == 409,
        })
    return payload


def request_id_conflict():
    return {
        "ok": False,
        "code": "request_id_conflict",
        "errors": {"_form": [{
            "code": "request_id_conflict",
            "message": (
                "Diese Speicheranfrage wurde bereits mit anderen Daten verwendet. "
                "Bitte Seite neu laden."
            ),
        }]},
        "replayed": False,
    }


def _locked_mutation_error(error, *, field):
    messages = {
        "duplicate_number": (
            "Diese Happy-Cleaning-Nummer ist bereits vergeben. "
            "Bitte Seite neu laden."
        ),
        "station_full": (
            "Diese Station ist bereits voll. Bitte Seite neu laden."
        ),
        "stale": (
            "Die Daten wurden zwischenzeitlich geändert. Bitte Seite neu laden."
        ),
        "number_required": (
            "Für eine Stationseinteilung ist eine Happy-Cleaning-Nummer "
            "erforderlich."
        ),
    }
    status = 409 if error.code in {"duplicate_number", "station_full", "stale"} else 422
    return KidEditCommandError(status, {
        "ok": False,
        "code": "conflict" if status == 409 else "validation_error",
        "errors": {field: [{
            "code": error.code,
            "message": messages.get(error.code, "Ungültige Formulardaten."),
        }]},
        "reload_required": status == 409,
        "replayed": False,
    })


def _period_label(period):
    unit = "Tag" if period.dauer == 1 else "Tage"
    return f"{period.get_woche_display()} ({period.dauer} {unit})"


def _assignment_target(assignment):
    if assignment is None:
        return KidEditCurrentHappyCleaningTarget("unassigned")
    if assignment.target_kind == "excused":
        return KidEditCurrentHappyCleaningTarget("excused")
    return KidEditCurrentHappyCleaningTarget(
        "station", station_id=assignment.station_id,
    )


def _snapshot(*, child, periods, active_links, events, assignments):
    focus_by_id = {
        focus.id: focus
        for period in periods
        for focus in period._kid_edit_focuses
    }
    return serialize_kid_edit_snapshot(
        child=child,
        active_periods=tuple(
            LoadedKidEditPeriod(
                period.id, period.woche, _period_label(period),
                period.swp_beginn, period.dauer,
            )
            for period in periods
        ),
        focus_links=tuple(
            LoadedKidEditFocusLink(
                focus_by_id[focus_id].schwerpunktzeit_id,
                focus_id,
                focus_by_id[focus_id].swp_name,
            )
            for focus_id in sorted(active_links)
        ),
        active_events=tuple(
            LoadedKidEditEvent(
                event.id, event.display_number,
                f"Happy Cleaning {event.display_number}", event.revision,
            )
            for event in events
        ),
        assignments=tuple(
            LoadedKidEditAssignment(
                event_id,
                assignment.version,
                assignment.target_kind,
                assignment.station_id,
                None if assignment.station is None else assignment.station.name,
                None if assignment.station is None else assignment.station.happy_cleaning_id,
            )
            for event_id, assignment in sorted(assignments.items())
        ),
    )


def _load_locked(turnus_id, child_id):
    turnus = (
        Turnus.objects.select_for_update(no_key=True)
        .filter(pk=turnus_id).first()
    )
    if turnus is None:
        return None
    periods = list(
        Schwerpunktzeit.objects.select_for_update()
        .filter(turnus_id=turnus_id).order_by("id")
    )
    period_ids = [period.id for period in periods]
    focuses = list(
        Schwerpunkte.objects.select_for_update()
        .filter(schwerpunktzeit_id__in=period_ids).order_by("id")
    )
    focuses_by_period = {period.id: [] for period in periods}
    for focus in focuses:
        focuses_by_period[focus.schwerpunktzeit_id].append(focus)
    for period in periods:
        period._kid_edit_focuses = tuple(focuses_by_period[period.id])

    events = list(
        HappyCleaning.objects.filter(turnus_id=turnus_id).order_by("id")
    )
    event_ids = [event.id for event in events]
    stations = list(
        HappyCleaningStation.objects.select_for_update()
        .filter(happy_cleaning_id__in=event_ids).order_by("id")
    )
    child = (
        Kinder.objects.select_for_update()
        .filter(pk=child_id, turnus_id=turnus_id).first()
    )
    if child is None:
        return None
    focus_ids = [focus.id for focus in focuses]
    active_links = frozenset(
        Kinder.schwerpunkte.through.objects.select_for_update(of=("self",))
        .filter(kinder_id=child.id, schwerpunkte_id__in=focus_ids)
        .order_by("id").values_list("schwerpunkte_id", flat=True)
    )
    assignments = {
        assignment.happy_cleaning_id: assignment
        for assignment in (
            HappyCleaningAssignment.objects.select_for_update(of=("self",))
            .select_related("station")
            .filter(child_id=child.id, happy_cleaning_id__in=event_ids)
            .order_by("happy_cleaning_id")
        )
    }
    events = list(
        HappyCleaning.objects.select_for_update()
        .filter(pk__in=event_ids).order_by("id")
    )
    stations_by_event = {event.id: [] for event in events}
    for station in stations:
        stations_by_event[station.happy_cleaning_id].append(station)
    current = KidEditCurrentState(
        turnus_id=turnus.id,
        child_id=child.id,
        edit_version=child.edit_version,
        number_version=child.happy_cleaning_number_version,
        happy_cleaning_number=child.happy_cleaning_number,
        raw_fields={
            field.storage_name: getattr(child, field.storage_name)
            for field in FIELD_CONTRACTS
        },
        periods=tuple(
            KidEditCurrentSwpPeriod(
                period.id,
                tuple(focus.id for focus in period._kid_edit_focuses),
                tuple(
                    focus.id for focus in period._kid_edit_focuses
                    if focus.id in active_links
                ),
            )
            for period in periods
        ),
        events=tuple(
            KidEditCurrentHappyCleaningEvent(
                event.id,
                tuple(station.id for station in stations_by_event[event.id]),
                0 if assignments.get(event.id) is None else assignments[event.id].version,
                _assignment_target(assignments.get(event.id)),
            )
            for event in events
        ),
    )
    return (turnus, child, periods, focuses, active_links, events, stations,
            stations_by_event, assignments, current)


def _swp_targets(command):
    result = {}
    for item in command.swp:
        if item.target.kind == "focus":
            result[item.period_id] = (item.target.focus_id,)
        elif item.target.kind == "preserve_legacy":
            result[item.period_id] = item.current_focus_ids
        else:
            result[item.period_id] = ()
    return result


def _merge_pre_errors(validated, pre_errors, current):
    contextual = (
        {} if not isinstance(validated, KidEditValidationError)
        else dict(validated.errors)
    )
    merged = {}
    if "_form" in contextual:
        merged["_form"] = contextual["_form"]
    for field in FIELD_CONTRACTS:
        items = []
        items.extend(contextual.get(field.api_name, ()))
        items.extend(pre_errors.get(field.api_name, ()))
        if items:
            merged[field.api_name] = tuple(items)
    for period in current.periods:
        key = f"swp.{period.period_id}"
        if key in contextual:
            merged[key] = contextual[key]
    if "happy_cleaning_number" in contextual:
        merged["happy_cleaning_number"] = contextual["happy_cleaning_number"]
    for event in current.events:
        key = f"happy_cleaning.{event.event_id}"
        if key in contextual:
            merged[key] = contextual[key]
    status = (
        validated.status if isinstance(validated, KidEditValidationError)
        else 422
    )
    return KidEditValidationError(
        status=status,
        code="conflict" if status == 409 else "validation_error",
        errors=merged,
        current_versions={
            "edit": current.edit_version,
            "happy_cleaning_number": current.number_version,
            "happy_cleaning": {
                str(event.event_id): event.current_assignment_version
                for event in current.events
            },
        },
    )


def execute_kid_edit(*, context, child_id, decoded, pre_errors=None):
    """Validate, plan, and commit the aggregate in one transaction."""
    with transaction.atomic():
        Profil.objects.select_for_update().get(user_id=context.actor_id)
        fingerprint = sign_kid_edit_request(
            decoded, turnus_id=context.turnus.id, child_id=child_id,
        )
        ledger = (
            HappyCleaningCommandRequest.objects.select_for_update()
            .filter(turnus=context.turnus, actor_id=context.actor_id,
                    request_id=decoded.request_id).first()
        )
        if ledger is not None:
            if (
                ledger.action != ACTION
                or not verify_kid_edit_request_fingerprint(
                    ledger.fingerprint, decoded,
                    turnus_id=context.turnus.id, child_id=child_id,
                )
            ):
                raise KidEditCommandError(409, request_id_conflict())
            return {**ledger.response, "replayed": True}, ledger.status_code
        loaded = _load_locked(context.turnus.id, child_id)
        if loaded is None:
            raise KidEditCommandError(404, {"ok": False, "code": "not_found"})
        (turnus, child, periods, focuses, active_links, events, stations,
         stations_by_event, assignments, current) = loaded
        validated = validate_kid_edit_command(decoded, current)
        if pre_errors:
            validated = _merge_pre_errors(validated, pre_errors, current)
        if isinstance(validated, KidEditValidationError):
            raise KidEditCommandError(
                validated.status, validation_error_response(validated),
            )
        focus_configuration = tuple(
            (period, period._kid_edit_focuses) for period in periods
        )
        swp_plan = plan_locked_swp_change(
            child=child, turnus=turnus,
            focus_configuration=focus_configuration,
            active_link_ids=active_links,
            requested_links_by_period=_swp_targets(validated),
            expected_version=validated.expected_edit_version,
        )
        try:
            number_plan = plan_locked_child_number(
                child=child, turnus_id=turnus.id,
                number=validated.happy_cleaning_number,
                expected_version=validated.expected_number_version,
            )
        except LockedMutationError as error:
            raise _locked_mutation_error(
                error, field="happy_cleaning_number",
            ) from error
        event_by_id = {event.id: event for event in events}
        station_by_id = {station.id: station for station in stations}
        assignment_plans = []
        for item in validated.happy_cleaning:
            target_station = (
                station_by_id[item.target.station_id]
                if item.target.kind == "station" else None
            )
            try:
                plan = plan_locked_assignment_change(
                    child=child, event=event_by_id[item.event_id],
                    current_assignment=assignments.get(item.event_id),
                    target_kind=item.target.kind, station=target_station,
                    expected_version=item.current_assignment_version,
                )
            except LockedMutationError as error:
                raise _locked_mutation_error(
                    error, field=f"happy_cleaning.{item.event_id}",
                ) from error
            assignment_plans.append((plan, target_station))

        scalar_fields = [
            name for name, value in validated.storage_fields.items()
            if getattr(child, name) != value
        ]
        aggregate_changed = bool(
            scalar_fields or swp_plan.changed or number_plan.changed
            or any(plan.changed for plan, _station in assignment_plans)
        )
        before = _snapshot(
            child=child, periods=periods, active_links=active_links,
            events=events, assignments=assignments,
        ) if aggregate_changed else None

        writer = _VersionedChildWrite(
            child=child,
            focus_ids_by_period={
                period.id: frozenset(
                    focus.id for focus in period._kid_edit_focuses
                ) for period in periods
            },
        )
        for name in scalar_fields:
            setattr(child, name, validated.storage_fields[name])
        writer.save_child(update_fields=scalar_fields)
        kid_edit_writes.apply_locked_swp_change(
            child=child, turnus=turnus,
            focus_configuration=focus_configuration,
            active_link_ids=active_links, plan=swp_plan,
        )
        happy_cleaning_assignment_commands.apply_locked_child_number(
            child=child, plan=number_plan,
        )
        changed_assignment_ids = {
            plan.event_id for plan, _station in assignment_plans if plan.changed
        }
        revisions = dict(bump_locked_event_revisions_once(
            turnus_id=turnus.id, number_changed=number_plan.changed,
            assignment_event_ids=changed_assignment_ids,
        ))
        for event in events:
            if event.id in revisions:
                event.revision = revisions[event.id]
        for plan, target_station in assignment_plans:
            if plan.changed:
                happy_cleaning_assignment_commands.apply_locked_assignment_change(
                    child=child, event=event_by_id[plan.event_id],
                    current_assignment=assignments.get(plan.event_id), plan=plan,
                    event_revision=revisions[plan.event_id],
                    target_station=target_station,
                )
        if scalar_fields or swp_plan.changed:
            child.edit_version += 1
            child.save(update_fields=("edit_version",))

        result = "updated" if aggregate_changed else "no_change"
        assignment_versions = {}
        if aggregate_changed:
            refreshed_assignments = {
                row.happy_cleaning_id: row
                for row in HappyCleaningAssignment.objects.select_related("station").filter(
                    child_id=child.id, happy_cleaning_id__in=event_by_id,
                )
            }
            active_after = swp_plan.target_link_ids
            after = _snapshot(
                child=child, periods=periods, active_links=active_after,
                events=events, assignments=refreshed_assignments,
            )
            api_name_by_storage = {
                field.storage_name: field.api_name for field in FIELD_CONTRACTS
            }
            changed_paths = [
                api_name_by_storage[name] for name in scalar_fields
            ]
            changed_paths.extend(
                f"swp.{item.period_id}" for item in validated.swp
                if tuple(item.current_focus_ids)
                != tuple(sorted(_swp_targets(validated)[item.period_id]))
            )
            if number_plan.changed:
                changed_paths.append("happy_cleaning_number")
            changed_paths.extend(
                f"happy_cleaning.{plan.event_id}"
                for plan, _station in assignment_plans if plan.changed
            )
            details = build_kid_edit_audit_details(before, after, changed_paths)
            record_audit_event(AuditEventData(
                turnus=turnus, actor_id=context.actor_id,
                actor_label=context.actor_label, action=ACTION,
                outcome="success", resource_type="child",
                resource_id=str(child.id),
                resource_label=f"{child.kid_vorname} {child.kid_nachname}".strip(),
                request_id=validated.request_id,
                client_ip=context.client_ip, user_agent=context.user_agent,
                details=details,
            ))
            assignment_versions = {
                str(event.id): (
                    0 if refreshed_assignments.get(event.id) is None
                    else refreshed_assignments[event.id].version
                ) for event in events
            }
        else:
            assignment_versions = {
                str(event.id): (
                    0 if assignments.get(event.id) is None
                    else assignments[event.id].version
                ) for event in events
            }
        response = {
            "ok": True, "result": result, "kid_id": child.id,
            "redirect": f"/kid_details/{child.id}",
            "versions": {
                "edit": child.edit_version,
                "happy_cleaning_number": child.happy_cleaning_number_version,
                "happy_cleaning_assignments": assignment_versions,
                "happy_cleaning_events": {
                    str(event.id): event.revision for event in events
                },
            },
            "replayed": False,
        }
        HappyCleaningCommandRequest.objects.create(
            turnus=turnus, actor_id=context.actor_id,
            request_id=validated.request_id, action=ACTION,
            response=response, fingerprint=fingerprint, status_code=200,
        )
        for event_id, revision in revisions.items():
            if number_plan.changed:
                publish_assignment_invalidation_on_commit({
                    "kind": "child_number", "happy_cleaning_id": event_id,
                    "revision": revision, "request_id": validated.request_id,
                })
            if event_id in changed_assignment_ids:
                publish_assignment_invalidation_on_commit({
                    "kind": "assignment", "happy_cleaning_id": event_id,
                    "revision": revision, "request_id": validated.request_id,
                })
        return response, 200
