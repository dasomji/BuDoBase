from contextlib import contextmanager
from dataclasses import dataclass

from django.db import transaction

from .kid_edit_contracts import (
    FIELD_CONTRACTS,
    canonicalize_storage_value,
)
from .models import Kinder, Schwerpunkte, Schwerpunktzeit, Turnus


COVERED_KINDER_FIELDS = tuple(
    field.storage_name for field in FIELD_CONTRACTS
)
_FIELD_CONTRACTS_BY_STORAGE_NAME = {
    field.storage_name: field for field in FIELD_CONTRACTS
}
_SCOPE_OWNED_FIELDS = {
    "id",
    "pk",
    "turnus",
    "turnus_id",
    "edit_version",
}


class ChildWriteScopeError(Exception):
    pass


class LockedSwpError(Exception):
    """Neutral failure raised by the lock-assuming SWP write seam."""

    def __init__(self, code, *, current_version=None):
        self.code = code
        self.current_version = current_version
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class LockedSwpPlan:
    child_id: int
    turnus_id: int
    expected_version: int
    focus_configuration: tuple
    source_link_ids: frozenset
    target_link_ids: frozenset
    changed: bool


def _canonical_locked_swp_configuration(*, turnus, focus_configuration):
    try:
        turnus_id = turnus.pk
        configuration = tuple(focus_configuration)
    except (AttributeError, TypeError):
        raise LockedSwpError("validation_error") from None

    if turnus_id is None:
        raise LockedSwpError("validation_error")

    canonical = []
    period_ids = set()
    focus_ids = set()
    for entry in configuration:
        try:
            period, focuses = entry
            period_id = period.pk
            period_turnus_id = period.turnus_id
            focuses = tuple(focuses)
        except (AttributeError, TypeError, ValueError):
            raise LockedSwpError("validation_error") from None

        if (
            period_id is None
            or period_turnus_id != turnus_id
            or period_id in period_ids
        ):
            raise LockedSwpError("validation_error")
        period_ids.add(period_id)

        period_focus_ids = []
        for focus in focuses:
            try:
                focus_id = focus.pk
                focus_period_id = focus.schwerpunktzeit_id
            except AttributeError:
                raise LockedSwpError("validation_error") from None
            if (
                focus_id is None
                or focus_period_id != period_id
                or focus_id in focus_ids
            ):
                raise LockedSwpError("validation_error")
            focus_ids.add(focus_id)
            period_focus_ids.append(focus_id)

        canonical.append((period_id, tuple(sorted(period_focus_ids))))

    return tuple(sorted(canonical)), frozenset(focus_ids)


def _validate_locked_swp_binding(*, child, turnus):
    try:
        child_id = child.pk
        turnus_id = turnus.pk
        child_turnus_id = child.turnus_id
    except AttributeError:
        raise LockedSwpError("not_found") from None
    if (
        child_id is None
        or turnus_id is None
        or child_turnus_id != turnus_id
    ):
        raise LockedSwpError("not_found")
    return child_id, turnus_id


def _canonical_requested_swp_links(
    *,
    focus_configuration,
    configured_focus_ids,
    source_link_ids,
    requested_links_by_period,
):
    try:
        requested_period_ids = set(requested_links_by_period)
    except TypeError:
        raise LockedSwpError("validation_error") from None

    configured_period_ids = {
        period_id for period_id, _focus_ids in focus_configuration
    }
    if requested_period_ids != configured_period_ids:
        raise LockedSwpError("validation_error")

    target_ids = set()
    for period_id, available_ids in focus_configuration:
        try:
            requested_ids = tuple(requested_links_by_period[period_id])
            distinct_requested_ids = set(requested_ids)
        except (KeyError, TypeError):
            raise LockedSwpError("validation_error") from None
        if len(distinct_requested_ids) != len(requested_ids):
            raise LockedSwpError("validation_error")
        for focus_id in requested_ids:
            if focus_id not in configured_focus_ids:
                raise LockedSwpError("not_found")
            if focus_id not in available_ids:
                raise LockedSwpError("not_found")
        if len(requested_ids) > 1 and distinct_requested_ids != (
            source_link_ids.intersection(available_ids)
        ):
            raise LockedSwpError("validation_error")
        target_ids.update(requested_ids)
    return frozenset(target_ids)


def _valid_plan_target(
    *,
    focus_configuration,
    source_link_ids,
    target_link_ids,
):
    if not isinstance(target_link_ids, frozenset):
        return False
    remaining = set(target_link_ids)
    configured = set()
    for _period_id, available_ids in focus_configuration:
        available_ids = set(available_ids)
        configured.update(available_ids)
        period_target_ids = remaining.intersection(available_ids)
        if len(period_target_ids) > 1 and period_target_ids != (
            source_link_ids.intersection(available_ids)
        ):
            return False
    return remaining.issubset(configured)


def plan_locked_swp_change(
    *,
    child,
    turnus,
    focus_configuration,
    active_link_ids,
    requested_links_by_period,
    expected_version,
):
    child_id, turnus_id = _validate_locked_swp_binding(
        child=child,
        turnus=turnus,
    )
    if child.edit_version != expected_version:
        raise LockedSwpError(
            "stale",
            current_version=child.edit_version,
        )

    canonical_configuration, configured_focus_ids = (
        _canonical_locked_swp_configuration(
            turnus=turnus,
            focus_configuration=focus_configuration,
        )
    )
    try:
        source_link_ids = frozenset(active_link_ids)
    except TypeError:
        raise LockedSwpError("validation_error") from None
    if not source_link_ids.issubset(configured_focus_ids):
        raise LockedSwpError("validation_error")

    target_link_ids = _canonical_requested_swp_links(
        focus_configuration=canonical_configuration,
        configured_focus_ids=configured_focus_ids,
        source_link_ids=source_link_ids,
        requested_links_by_period=requested_links_by_period,
    )
    return LockedSwpPlan(
        child_id=child_id,
        turnus_id=turnus_id,
        expected_version=expected_version,
        focus_configuration=canonical_configuration,
        source_link_ids=source_link_ids,
        target_link_ids=target_link_ids,
        changed=source_link_ids != target_link_ids,
    )


def apply_locked_swp_change(
    *,
    child,
    turnus,
    focus_configuration,
    active_link_ids,
    plan,
):
    if not isinstance(plan, LockedSwpPlan):
        raise LockedSwpError("plan_mismatch")
    if (
        not isinstance(plan.focus_configuration, tuple)
        or not isinstance(plan.source_link_ids, frozenset)
        or not isinstance(plan.target_link_ids, frozenset)
        or not isinstance(plan.changed, bool)
    ):
        raise LockedSwpError("plan_mismatch")

    try:
        child_id = child.pk
        turnus_id = turnus.pk
        child_turnus_id = child.turnus_id
    except AttributeError:
        raise LockedSwpError("plan_mismatch") from None
    if (
        child_id != plan.child_id
        or turnus_id != plan.turnus_id
        or child_turnus_id != turnus_id
    ):
        raise LockedSwpError("plan_mismatch")

    if child.edit_version != plan.expected_version:
        raise LockedSwpError(
            "stale",
            current_version=child.edit_version,
        )

    try:
        canonical_configuration, configured_focus_ids = (
            _canonical_locked_swp_configuration(
                turnus=turnus,
                focus_configuration=focus_configuration,
            )
        )
        current_link_ids = frozenset(active_link_ids)
    except LockedSwpError:
        raise LockedSwpError("plan_mismatch") from None
    except TypeError:
        raise LockedSwpError("plan_mismatch") from None

    if canonical_configuration != plan.focus_configuration:
        raise LockedSwpError("plan_mismatch")
    if current_link_ids != plan.source_link_ids:
        raise LockedSwpError(
            "stale",
            current_version=child.edit_version,
        )
    if (
        not plan.source_link_ids.issubset(configured_focus_ids)
        or not _valid_plan_target(
            focus_configuration=canonical_configuration,
            source_link_ids=plan.source_link_ids,
            target_link_ids=plan.target_link_ids,
        )
        or plan.changed
        != (plan.source_link_ids != plan.target_link_ids)
    ):
        raise LockedSwpError("plan_mismatch")

    if not plan.changed:
        return False

    remove_ids = plan.source_link_ids - plan.target_link_ids
    add_ids = plan.target_link_ids - plan.source_link_ids
    through = Kinder.schwerpunkte.through
    if remove_ids:
        through.objects.filter(
            kinder_id=child_id,
            schwerpunkte_id__in=remove_ids,
        ).delete()
    if add_ids:
        through.objects.bulk_create(
            [
                through(kinder_id=child_id, schwerpunkte_id=focus_id)
                for focus_id in sorted(add_ids)
            ]
        )
    return True


def _canonical_field_value(field_name, value):
    field = _FIELD_CONTRACTS_BY_STORAGE_NAME[field_name]
    return canonicalize_storage_value(field, value).api_value


def _canonical_child_snapshot(child):
    return tuple(
        _canonical_field_value(field_name, getattr(child, field_name))
        for field_name in COVERED_KINDER_FIELDS
    )


def _lock_swp_configuration(turnus_id):
    turnus_exists = Turnus.objects.select_for_update().filter(
        pk=turnus_id,
    ).exists()
    if not turnus_exists:
        raise ChildWriteScopeError(
            "The active Turnus is unavailable."
        )

    period_ids = tuple(
        Schwerpunktzeit.objects.select_for_update()
        .filter(turnus_id=turnus_id)
        .order_by("id")
        .values_list("id", flat=True)
    )
    focus_rows = tuple(
        Schwerpunkte.objects.select_for_update()
        .filter(schwerpunktzeit_id__in=period_ids)
        .order_by("id")
        .values_list("id", "schwerpunktzeit_id")
    )
    focus_ids_by_period = {period_id: set() for period_id in period_ids}
    for focus_id, period_id in focus_rows:
        focus_ids_by_period[period_id].add(focus_id)
    return {
        period_id: frozenset(focus_ids)
        for period_id, focus_ids in focus_ids_by_period.items()
    }


def _configured_focus_ids(focus_ids_by_period):
    return frozenset(
        focus_id
        for focus_ids in focus_ids_by_period.values()
        for focus_id in focus_ids
    )


def _lock_active_swp_links(*, child_id, focus_ids):
    through = Kinder.schwerpunkte.through
    if not focus_ids:
        return frozenset()
    return frozenset(
        through.objects.select_for_update(of=("self",))
        .filter(
            kinder_id=child_id,
            schwerpunkte_id__in=focus_ids,
        )
        .order_by("id")
        .values_list("schwerpunkte_id", flat=True)
    )


def _active_swp_snapshot(*, child_id, focus_ids):
    if not focus_ids:
        return frozenset()
    return frozenset(
        Kinder.schwerpunkte.through.objects.filter(
            kinder_id=child_id,
            schwerpunkte_id__in=focus_ids,
        ).values_list("schwerpunkte_id", flat=True)
    )


class _VersionedChildWrite:
    def __init__(self, *, child, focus_ids_by_period):
        self.child = child
        self._focus_ids_by_period = focus_ids_by_period
        self._original_covered_values = {
            field_name: getattr(child, field_name)
            for field_name in COVERED_KINDER_FIELDS
        }
        self._persisted_covered_values = dict(
            self._original_covered_values
        )

    def save_child(self, *, update_fields):
        update_fields = tuple(update_fields)
        if _SCOPE_OWNED_FIELDS.intersection(update_fields):
            raise ChildWriteScopeError(
                "Scope-owned child fields cannot be saved directly."
            )

        persisted_fields = []
        for field_name in update_fields:
            if field_name in COVERED_KINDER_FIELDS:
                original_value = self._original_covered_values[field_name]
                requested_value = getattr(self.child, field_name)
                if (
                    _canonical_field_value(field_name, requested_value)
                    == _canonical_field_value(field_name, original_value)
                ):
                    setattr(self.child, field_name, original_value)
                    if (
                        self._persisted_covered_values[field_name]
                        == original_value
                    ):
                        continue
            persisted_fields.append(field_name)

        if not persisted_fields:
            return

        self.child.save(update_fields=tuple(persisted_fields))
        for field_name in persisted_fields:
            if field_name in COVERED_KINDER_FIELDS:
                self._persisted_covered_values[field_name] = getattr(
                    self.child,
                    field_name,
                )

    def validate_swp_focus(self, *, period_id, focus_id):
        available_ids = self._focus_ids_by_period.get(period_id)
        if available_ids is None:
            raise ChildWriteScopeError(
                "The Schwerpunktzeit is unavailable in the active Turnus."
            )
        if focus_id not in available_ids:
            raise ChildWriteScopeError(
                "A Schwerpunkt is unavailable in the active Turnus period."
            )

    def set_swp_links(self, *, period_id, focus_ids):
        available_ids = self._focus_ids_by_period.get(period_id)
        if available_ids is None:
            raise ChildWriteScopeError(
                "The Schwerpunktzeit is unavailable in the active Turnus."
            )

        requested_ids = frozenset(focus_ids)
        if not requested_ids.issubset(available_ids):
            raise ChildWriteScopeError(
                "A Schwerpunkt is unavailable in the active Turnus period."
            )

        through = Kinder.schwerpunkte.through
        current_ids = frozenset(
            through.objects.select_for_update(of=("self",))
            .filter(
                kinder_id=self.child.id,
                schwerpunkte_id__in=available_ids,
            )
            .order_by("id")
            .values_list("schwerpunkte_id", flat=True)
        )
        remove_ids = current_ids - requested_ids
        add_ids = requested_ids - current_ids

        if remove_ids:
            through.objects.filter(
                kinder_id=self.child.id,
                schwerpunkte_id__in=remove_ids,
            ).delete()
        if add_ids:
            self.child.schwerpunkte.add(*add_ids)

    def set_swp_link(self, *, period_id, focus_id, present):
        self.validate_swp_focus(
            period_id=period_id,
            focus_id=focus_id,
        )
        through = Kinder.schwerpunkte.through
        link = through.objects.select_for_update(of=("self",)).filter(
            kinder_id=self.child.id,
            schwerpunkte_id=focus_id,
        )
        exists = link.exists()
        if present and not exists:
            self.child.schwerpunkte.add(focus_id)
        elif not present and exists:
            link.delete()


@contextmanager
def versioned_child_write(*, turnus_id, child_id):
    with transaction.atomic():
        focus_ids_by_period = _lock_swp_configuration(turnus_id)
        configured_focus_ids = _configured_focus_ids(focus_ids_by_period)
        child = (
            Kinder.objects.select_for_update()
            .filter(pk=child_id, turnus_id=turnus_id)
            .first()
        )
        if child is None:
            raise ChildWriteScopeError(
                "The child is unavailable in the active Turnus."
            )

        original_version = child.edit_version
        original_child = _canonical_child_snapshot(child)
        original_swp = _lock_active_swp_links(
            child_id=child.id,
            focus_ids=configured_focus_ids,
        )
        write = _VersionedChildWrite(
            child=child,
            focus_ids_by_period=focus_ids_by_period,
        )

        yield write

        persisted_child = Kinder.objects.filter(
            pk=child_id,
            turnus_id=turnus_id,
        ).first()
        if persisted_child is None:
            raise ChildWriteScopeError(
                "The child left the active Turnus write scope."
            )
        if persisted_child.edit_version != original_version:
            raise ChildWriteScopeError(
                "edit_version is owned by the versioned child-write scope."
            )

        current_child = _canonical_child_snapshot(persisted_child)
        current_swp = _active_swp_snapshot(
            child_id=child_id,
            focus_ids=configured_focus_ids,
        )
        if current_child != original_child or current_swp != original_swp:
            persisted_child.edit_version = original_version + 1
            persisted_child.save(update_fields=("edit_version",))
            child.edit_version = persisted_child.edit_version
