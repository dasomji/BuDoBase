from contextlib import contextmanager

from django.db import transaction

from .models import Kinder, Schwerpunkte, Schwerpunktzeit, Turnus
from .text_cleaning import (
    DEFAULT_EMPTY_VALUES,
    FOOD_EMPTY_VALUES,
    REQUEST_EMPTY_VALUES,
)


COVERED_KINDER_FIELDS = (
    "kid_vorname",
    "kid_nachname",
    "sex",
    "kid_birthday",
    "turnus_dauer",
    "geschwister",
    "zeltwunsch",
    "budo_erfahrung",
    "sozialversicherungsnr",
    "illness",
    "drugs",
    "vegetarisch",
    "special_food_description",
    "swimmer",
    "einverstaendnis_erklaerung",
    "rezeptfreie_medikamente",
    "rezept_medikamente",
    "tetanusimpfung",
    "zeckenimpfung",
    "anmelde_organisation",
    "anmelder_vorname",
    "anmelder_nachname",
    "anmelder_email",
    "anmelder_mobil",
    "hauptversichert_bei",
    "notfall_kontakte",
    "budo_family",
)

_SEMANTIC_BLANKS = {
    "geschwister": REQUEST_EMPTY_VALUES,
    "zeltwunsch": REQUEST_EMPTY_VALUES,
    "illness": DEFAULT_EMPTY_VALUES,
    "drugs": DEFAULT_EMPTY_VALUES,
    "special_food_description": FOOD_EMPTY_VALUES,
}
_BOOLEAN_FIELDS = {
    "budo_erfahrung",
    "einverstaendnis_erklaerung",
}
_NON_TEXT_FIELDS = _BOOLEAN_FIELDS | {"kid_birthday", "turnus_dauer"}
_SCOPE_OWNED_FIELDS = {
    "id",
    "pk",
    "turnus",
    "turnus_id",
    "edit_version",
}


class ChildWriteScopeError(Exception):
    pass


def _normalized_text(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _canonical_controlled_value(field_name, value):
    normalized = _normalized_text(value)
    lowered = normalized.lower()

    if field_name == "sex":
        if lowered in {"", "nan", "none", "-"}:
            return None
        if lowered in {"weiblich", "männlich", "divers"}:
            return lowered
    elif field_name == "vegetarisch":
        if lowered in {"", "nan", "none", "-"}:
            return None
        if lowered == "ja":
            return True
        if lowered == "nein":
            return False
    elif field_name == "budo_family":
        if normalized == "":
            return None
        if normalized in {"S", "M", "L", "XL"}:
            return normalized

    return normalized


def _canonical_field_value(field_name, value):
    if field_name in _NON_TEXT_FIELDS:
        return value
    if field_name in {"sex", "vegetarisch", "budo_family"}:
        return _canonical_controlled_value(field_name, value)

    normalized = _normalized_text(value)
    empty_values = _SEMANTIC_BLANKS.get(field_name)
    if empty_values is not None and normalized.lower() in empty_values:
        return ""
    return normalized


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
