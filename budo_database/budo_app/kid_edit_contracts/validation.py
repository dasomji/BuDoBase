"""Pure contextual validation for decoded kid-edit commands."""

from dataclasses import dataclass
from types import MappingProxyType

from . import (
    FIELD_CONTRACTS,
    KidEditContractError,
    canonicalize_storage_value,
    canonicalize_submission_value,
    is_canonical_no_op,
)
from .decoder import KidEditFieldError, KidEditRequest, _FIELD_LABELS
from .signing import (
    has_legacy_token_syntax,
    verify_field_baseline,
    verify_legacy_preserve_value,
    verify_swp_baseline,
)


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} is invalid")
    if value <= 0:
        raise ValueError(f"{name} is invalid")


def _sorted_positive_ids(values, name):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} is invalid")
    try:
        copied = tuple(values)
    except TypeError:
        raise TypeError(f"{name} is invalid") from None
    for value in copied:
        _positive_integer(value, name)
    if len(set(copied)) != len(copied):
        raise ValueError(f"{name} must be unique")
    return tuple(sorted(copied))


@dataclass(frozen=True, slots=True)
class KidEditCurrentSwpPeriod:
    period_id: int
    available_focus_ids: tuple
    current_focus_ids: tuple

    def __post_init__(self):
        _positive_integer(self.period_id, "period_id")
        available = _sorted_positive_ids(
            self.available_focus_ids,
            "available_focus_ids",
        )
        current = _sorted_positive_ids(
            self.current_focus_ids,
            "current_focus_ids",
        )
        if not set(current).issubset(available):
            raise ValueError("current_focus_ids are unavailable")
        object.__setattr__(self, "available_focus_ids", available)
        object.__setattr__(self, "current_focus_ids", current)


@dataclass(frozen=True, slots=True)
class KidEditCurrentHappyCleaningTarget:
    kind: str
    station_id: int | None = None

    def __post_init__(self):
        if self.kind == "station":
            _positive_integer(self.station_id, "station_id")
        elif self.kind in {"unassigned", "excused"}:
            if self.station_id is not None:
                raise ValueError("station_id is not allowed")
        else:
            raise ValueError("invalid target kind")


@dataclass(frozen=True, slots=True)
class KidEditCurrentHappyCleaningEvent:
    event_id: int
    available_station_ids: tuple
    current_assignment_version: int
    current_target: KidEditCurrentHappyCleaningTarget

    def __post_init__(self):
        _positive_integer(self.event_id, "event_id")
        if (
            isinstance(self.current_assignment_version, bool)
            or not isinstance(self.current_assignment_version, int)
            or self.current_assignment_version < 0
        ):
            raise TypeError("current_assignment_version is invalid")
        available = _sorted_positive_ids(
            self.available_station_ids,
            "available_station_ids",
        )
        if not isinstance(
            self.current_target,
            KidEditCurrentHappyCleaningTarget,
        ):
            raise TypeError("current_target is invalid")
        if (self.current_assignment_version == 0) != (
            self.current_target.kind == "unassigned"
        ):
            raise ValueError("assignment version and target are inconsistent")
        if (
            self.current_target.kind == "station"
            and self.current_target.station_id not in available
        ):
            raise ValueError("current station is unavailable")
        object.__setattr__(self, "available_station_ids", available)


@dataclass(frozen=True, slots=True, repr=False)
class KidEditCurrentState:
    turnus_id: int
    child_id: int
    edit_version: int
    number_version: int
    happy_cleaning_number: int | None
    raw_fields: object
    periods: tuple
    events: tuple

    def __post_init__(self):
        _positive_integer(self.turnus_id, "turnus_id")
        _positive_integer(self.child_id, "child_id")
        _positive_integer(self.edit_version, "edit_version")
        _positive_integer(self.number_version, "number_version")
        if self.happy_cleaning_number is not None:
            _positive_integer(
                self.happy_cleaning_number,
                "happy_cleaning_number",
            )
        raw_fields = dict(self.raw_fields)
        expected_fields = tuple(
            field.storage_name for field in FIELD_CONTRACTS
        )
        if set(raw_fields) != set(expected_fields):
            raise ValueError("raw_fields do not match the contract")
        periods = tuple(self.periods)
        events = tuple(self.events)
        if not all(
            isinstance(item, KidEditCurrentSwpPeriod) for item in periods
        ):
            raise TypeError("periods are invalid")
        if not all(
            isinstance(item, KidEditCurrentHappyCleaningEvent)
            for item in events
        ):
            raise TypeError("events are invalid")
        periods = tuple(sorted(periods, key=lambda item: item.period_id))
        events = tuple(sorted(events, key=lambda item: item.event_id))
        if len({item.period_id for item in periods}) != len(periods):
            raise ValueError("period IDs must be unique")
        if len({item.event_id for item in events}) != len(events):
            raise ValueError("event IDs must be unique")
        object.__setattr__(
            self,
            "raw_fields",
            MappingProxyType(
                {
                    field_name: raw_fields[field_name]
                    for field_name in expected_fields
                }
            ),
        )
        object.__setattr__(self, "periods", periods)
        object.__setattr__(self, "events", events)

    def __repr__(self):
        return (
            f"KidEditCurrentState(turnus_id={self.turnus_id!r}, "
            f"child_id={self.child_id!r}, <redacted>)"
        )


@dataclass(frozen=True, slots=True, repr=False)
class ValidatedKidEditSwp:
    period_id: int
    current_focus_ids: tuple
    target: object

    def __repr__(self):
        return f"ValidatedKidEditSwp(period_id={self.period_id!r}, <redacted>)"


@dataclass(frozen=True, slots=True)
class ValidatedKidEditHappyCleaning:
    event_id: int
    current_assignment_version: int
    target: object


@dataclass(frozen=True, slots=True, repr=False)
class ValidatedKidEditCommand:
    request_id: str
    turnus_id: int
    child_id: int
    expected_edit_version: int
    storage_fields: object
    swp: tuple
    happy_cleaning_number: int | None
    expected_number_version: int
    happy_cleaning: tuple

    def __repr__(self):
        return (
            f"ValidatedKidEditCommand(turnus_id={self.turnus_id!r}, "
            f"child_id={self.child_id!r}, <redacted>)"
        )


@dataclass(frozen=True, slots=True, repr=False)
class KidEditValidationError:
    status: int
    code: str
    errors: object
    current_versions: object

    def __repr__(self):
        return (
            f"KidEditValidationError(status={self.status!r}, "
            f"code={self.code!r}, current_versions=<numeric>)"
        )


def _deep_versions(current):
    return MappingProxyType(
        {
            "edit": current.edit_version,
            "happy_cleaning_number": current.number_version,
            "happy_cleaning": MappingProxyType(
                {
                    str(event.event_id): event.current_assignment_version
                    for event in sorted(
                        current.events,
                        key=lambda item: item.event_id,
                    )
                }
            ),
        }
    )


def _validation_error(*, current, errors, conflict):
    return KidEditValidationError(
        status=409 if conflict else 422,
        code="conflict" if conflict else "validation_error",
        errors=MappingProxyType(
            {field: tuple(items) for field, items in errors.items()}
        ),
        current_versions=_deep_versions(current),
    )


def _item(code, message):
    return KidEditFieldError(code=code, message=message)


_CONFIGURATION_CHANGED = (
    "Die Einteilungen wurden zwischenzeitlich geändert. Bitte Seite neu laden."
)
_INVALID_EMAIL = "Bitte eine gültige E-Mail-Adresse eingeben."
_UNAVAILABLE = "Diese Auswahl ist nicht mehr verfügbar. Bitte Seite neu laden."
_FORM_STALE = "Die Daten wurden zwischenzeitlich geändert. Bitte Seite neu laden."
_SWP_STALE = (
    "Diese Schwerpunkt-Einteilung wurde zwischenzeitlich geändert. "
    "Bitte Seite neu laden."
)
_NUMBER_STALE = (
    "Die Happy-Cleaning-Nummer wurde zwischenzeitlich geändert. "
    "Bitte Seite neu laden."
)
_EVENT_STALE = (
    "Diese Happy-Cleaning-Einteilung wurde zwischenzeitlich geändert. "
    "Bitte Seite neu laden."
)
_NUMBER_REQUIRED = (
    "Für eine Stationseinteilung ist eine Happy-Cleaning-Nummer erforderlich."
)
_EVENT_NUMBER_REQUIRED = (
    "Vor der Stationseinteilung muss eine Happy-Cleaning-Nummer vergeben werden."
)


def _field_stale(field_name):
    return (
        f"{_FIELD_LABELS[field_name]} wurde zwischenzeitlich geändert. "
        "Bitte Seite neu laden."
    )


def _configuration_matches(decoded, current):
    return (
        {item.period_id for item in decoded.swp}
        == {item.period_id for item in current.periods}
        and {item.event_id for item in decoded.happy_cleaning}
        == {item.event_id for item in current.events}
    )


def _field_validation(decoded, current):
    errors = {}
    storage_fields = {}
    stale_baseline = False
    for field in FIELD_CONTRACTS:
        raw_value = current.raw_fields[field.storage_name]
        current_value = canonicalize_storage_value(field, raw_value).api_value
        baseline_matches = verify_field_baseline(
            decoded.field_baselines[field.api_name],
            turnus_id=current.turnus_id,
            child_id=current.child_id,
            field_name=field.api_name,
            canonical_value=current_value,
        )
        if not baseline_matches:
            errors[field.api_name] = [
                _item("stale", _field_stale(field.api_name))
            ]
            stale_baseline = True
            continue

        submitted = decoded.fields[field.api_name]
        if has_legacy_token_syntax(submitted):
            if verify_legacy_preserve_value(
                submitted,
                turnus_id=current.turnus_id,
                child_id=current.child_id,
                field_name=field.api_name,
                raw_storage_value=raw_value,
            ):
                storage_fields[field.storage_name] = raw_value
            else:
                errors[field.api_name] = [
                    _item("stale", _field_stale(field.api_name))
                ]
                stale_baseline = True
            continue

        try:
            canonical = canonicalize_submission_value(field, submitted)
        except KidEditContractError as error:
            if (
                field.api_name == "registrant_email"
                and error.code == "invalid_email"
                and submitted == current_value
            ):
                storage_fields[field.storage_name] = raw_value
            else:
                errors[field.api_name] = [
                    _item(error.code, _INVALID_EMAIL)
                ]
            continue

        storage_fields[field.storage_name] = (
            raw_value
            if is_canonical_no_op(field, raw_value, submitted)
            else canonical.storage_value
        )
    return storage_fields, errors, stale_baseline


def _swp_validation(decoded, current):
    periods = {period.period_id: period for period in current.periods}
    errors = {}
    validated = []
    stale_baseline = False
    for submitted in sorted(decoded.swp, key=lambda item: item.period_id):
        period = periods[submitted.period_id]
        baseline_matches = verify_swp_baseline(
            submitted.baseline,
            turnus_id=current.turnus_id,
            child_id=current.child_id,
            period_id=period.period_id,
            current_focus_ids=period.current_focus_ids,
        )
        if not baseline_matches:
            errors[f"swp.{period.period_id}"] = [
                _item("stale", _SWP_STALE)
            ]
            stale_baseline = True
            continue

        target = submitted.target
        if target.kind == "focus" and (
            target.focus_id not in period.available_focus_ids
        ):
            errors[f"swp.{period.period_id}"] = [
                _item("unavailable", _UNAVAILABLE)
            ]
            continue
        if target.kind == "preserve_legacy" and not verify_swp_baseline(
            target.token,
            turnus_id=current.turnus_id,
            child_id=current.child_id,
            period_id=period.period_id,
            current_focus_ids=period.current_focus_ids,
        ):
            errors[f"swp.{period.period_id}"] = [
                _item("stale", _SWP_STALE)
            ]
            stale_baseline = True
            continue
        validated.append(
            ValidatedKidEditSwp(
                period_id=period.period_id,
                current_focus_ids=period.current_focus_ids,
                target=target,
            )
        )
    return tuple(validated), errors, stale_baseline


def _happy_cleaning_validation(decoded, current):
    events = {event.event_id: event for event in current.events}
    errors = {}
    validated = []
    for submitted in sorted(
        decoded.happy_cleaning,
        key=lambda item: item.event_id,
    ):
        event = events[submitted.event_id]
        key = f"happy_cleaning.{event.event_id}"
        if (
            submitted.expected_assignment_version
            != event.current_assignment_version
        ):
            errors[key] = [_item("stale", _EVENT_STALE)]
            continue
        if submitted.target.kind == "station" and (
            submitted.target.station_id not in event.available_station_ids
        ):
            errors[key] = [_item("unavailable", _UNAVAILABLE)]
            continue
        validated.append(
            ValidatedKidEditHappyCleaning(
                event_id=event.event_id,
                current_assignment_version=event.current_assignment_version,
                target=submitted.target,
            )
        )
    return tuple(validated), errors


def validate_kid_edit_command(decoded, current):
    """Validate decoded intent against an authoritative caller-held snapshot."""
    if not isinstance(decoded, KidEditRequest) or not isinstance(
        current,
        KidEditCurrentState,
    ):
        errors = {"_form": [_item("invalid_type", "Ungültige Formulardaten.")]}
        if isinstance(current, KidEditCurrentState):
            return _validation_error(
                current=current,
                errors=errors,
                conflict=False,
            )
        raise TypeError("current must be KidEditCurrentState")

    if not _configuration_matches(decoded, current):
        return _validation_error(
            current=current,
            errors={
                "_form": [
                    _item("configuration_changed", _CONFIGURATION_CHANGED)
                ]
            },
            conflict=True,
        )

    storage_fields, field_errors, field_stale = _field_validation(
        decoded,
        current,
    )
    swp, swp_errors, swp_stale = _swp_validation(decoded, current)
    happy_cleaning, event_errors = _happy_cleaning_validation(decoded, current)

    number_errors = {}
    if decoded.expected_number_version != current.number_version:
        number_errors["happy_cleaning_number"] = [
            _item("stale", _NUMBER_STALE)
        ]

    errors = {}
    for field in FIELD_CONTRACTS:
        if field.api_name in field_errors:
            errors[field.api_name] = field_errors[field.api_name]
    for period in sorted(current.periods, key=lambda item: item.period_id):
        key = f"swp.{period.period_id}"
        if key in swp_errors:
            errors[key] = swp_errors[key]
    errors.update(number_errors)
    for event in sorted(current.events, key=lambda item: item.event_id):
        key = f"happy_cleaning.{event.event_id}"
        if key in event_errors:
            errors[key] = event_errors[key]

    has_baseline_stale = field_stale or swp_stale
    if (
        decoded.expected_edit_version != current.edit_version
        and not has_baseline_stale
    ):
        errors = {"_form": [_item("stale", _FORM_STALE)], **errors}

    station_keys = tuple(
        f"happy_cleaning.{item.event_id}"
        for item in decoded.happy_cleaning
        if item.target.kind == "station"
    )
    if decoded.happy_cleaning_number is None and station_keys:
        errors.setdefault("happy_cleaning_number", []).append(
            _item("number_required", _NUMBER_REQUIRED)
        )
        for key in station_keys:
            errors.setdefault(key, []).append(
                _item("number_required", _EVENT_NUMBER_REQUIRED)
            )

    if errors:
        canonically_ordered = {}
        if "_form" in errors:
            canonically_ordered["_form"] = errors["_form"]
        for field in FIELD_CONTRACTS:
            if field.api_name in errors:
                canonically_ordered[field.api_name] = errors[field.api_name]
        for period in sorted(current.periods, key=lambda item: item.period_id):
            key = f"swp.{period.period_id}"
            if key in errors:
                canonically_ordered[key] = errors[key]
        if "happy_cleaning_number" in errors:
            canonically_ordered["happy_cleaning_number"] = errors[
                "happy_cleaning_number"
            ]
        for event in sorted(current.events, key=lambda item: item.event_id):
            key = f"happy_cleaning.{event.event_id}"
            if key in errors:
                canonically_ordered[key] = errors[key]
        errors = canonically_ordered

    if errors:
        conflict_codes = {"stale", "configuration_changed"}
        conflict = any(
            item.code in conflict_codes
            for items in errors.values()
            for item in items
        )
        return _validation_error(
            current=current,
            errors=errors,
            conflict=conflict,
        )

    return ValidatedKidEditCommand(
        request_id=decoded.request_id,
        turnus_id=current.turnus_id,
        child_id=current.child_id,
        expected_edit_version=decoded.expected_edit_version,
        storage_fields=MappingProxyType(storage_fields),
        swp=swp,
        happy_cleaning_number=decoded.happy_cleaning_number,
        expected_number_version=decoded.expected_number_version,
        happy_cleaning=happy_cleaning,
    )
