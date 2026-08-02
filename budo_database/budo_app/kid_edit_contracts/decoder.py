"""Pure structural decoding for kid-edit requests."""

from dataclasses import dataclass
import json
from types import MappingProxyType

from . import (
    FIELD_CONTRACTS,
    HAPPY_CLEANING_NUMBER_CONTRACT,
    KidEditContractError,
    canonicalize_submission_value,
)
from .signing import has_baseline_token_syntax, has_legacy_token_syntax


BODY_LIMIT = 128 * 1024
_TOP_LEVEL_KEYS = frozenset(
    {
        "request_id",
        "expected_edit_version",
        "field_baselines",
        "fields",
        "swp",
        "happy_cleaning_number",
        "expected_number_version",
        "happy_cleaning",
    }
)
_FIELD_NAMES = tuple(field.api_name for field in FIELD_CONTRACTS)
_FIELD_NAME_SET = frozenset(_FIELD_NAMES)
_LEGACY_FIELDS = frozenset(
    {"sex", "stay_weeks", "vegetarian", "budo_family"}
)


@dataclass(frozen=True, slots=True)
class KidEditFieldError:
    code: str
    message: str


@dataclass(frozen=True, slots=True, repr=False)
class KidEditParseError:
    status: int
    code: str
    errors: object

    def __repr__(self):
        return (
            f"KidEditParseError(status={self.status!r}, "
            f"code={self.code!r})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class SwpTarget:
    kind: str
    focus_id: int | None = None
    token: str | None = None

    def __repr__(self):
        return f"SwpTarget(kind={self.kind!r}, <redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class SwpItem:
    period_id: int
    baseline: str
    target: SwpTarget

    def __repr__(self):
        return (
            f"SwpItem(period_id={self.period_id!r}, "
            f"target={self.target!r}, <redacted>)"
        )


@dataclass(frozen=True, slots=True)
class HappyCleaningTarget:
    kind: str
    station_id: int | None = None


@dataclass(frozen=True, slots=True)
class HappyCleaningItem:
    event_id: int
    expected_assignment_version: int
    target: HappyCleaningTarget


@dataclass(frozen=True, slots=True, repr=False)
class KidEditRequest:
    request_id: str
    expected_edit_version: int
    field_baselines: object
    fields: object
    swp: tuple
    happy_cleaning_number: int | None
    expected_number_version: int
    happy_cleaning: tuple

    def __repr__(self):
        return "KidEditRequest(<normalized>)"


_FIELD_LABELS = {
    "first_name": "Vorname",
    "last_name": "Nachname",
    "sex": "Geschlecht",
    "birthday": "Geburtstag",
    "stay_weeks": "Aufenthaltsdauer",
    "siblings": "Geschwister",
    "tent_request": "Zeltwunsch",
    "budo_experience": "BuDo-Erfahrung",
    "social_security_number": "Sozialversicherungsnummer",
    "illness": "Krankheiten und Besonderheiten",
    "drugs": "Medikamente",
    "vegetarian": "Vegetarisch",
    "special_food": "Besondere Ernährung",
    "swimmer": "Schwimmkenntnisse",
    "consent": "Einverständniserklärung",
    "over_the_counter_medication": "Rezeptfreie Medikamente",
    "prescription_medication": "Rezeptpflichtige Medikamente",
    "tetanus": "Tetanusimpfung",
    "tick_vaccine": "Zeckenimpfung",
    "organization": "Organisation",
    "registrant_first_name": "Vorname der anmeldenden Person",
    "registrant_last_name": "Nachname der anmeldenden Person",
    "registrant_email": "E-Mail der anmeldenden Person",
    "registrant_phone": "Mobilnummer der anmeldenden Person",
    "insured_with": "Hauptversichert bei",
    "emergency_contacts": "Notfallkontakte",
    "budo_family": "BuDo-Familie",
}
_FIELD_LIMITS = {
    field.api_name: field.max_length
    for field in FIELD_CONTRACTS
    if field.max_length is not None
}
_MESSAGES = {
    "invalid_type": "Die Formulardaten haben ein ungültiges Format.",
    "required": "Dieses Feld ist erforderlich.",
    "too_long": "Der eingegebene Wert ist zu lang.",
    "control": "Der eingegebene Text enthält ungültige Zeichen.",
    "single_line": "Bitte nur eine Zeile eingeben.",
    "invalid_date": "Bitte ein gültiges Datum eingeben.",
    "invalid_email": "Bitte eine gültige E-Mail-Adresse eingeben.",
    "invalid_choice": "Bitte eine gültige Auswahl treffen.",
    "invalid_number": "Happy-Cleaning-Nummer muss eine positive ganze Zahl sein.",
    "duplicate_id": "Diese Auswahl wurde mehrfach übermittelt. Bitte Seite neu laden.",
    "missing_field": "Die Formulardaten sind unvollständig. Bitte Seite neu laden.",
    "unknown_field": "Die Formulardaten enthalten unbekannte Felder. Bitte Seite neu laden.",
    "invalid_json": "Die Anfrage enthält kein gültiges JSON.",
    "unsupported_media_type": "Bitte JSON-Daten senden.",
    "request_too_large": "Die Anfrage ist zu groß.",
}
_FIELD_MESSAGES = {
    ("first_name", "required"): "Vorname ist erforderlich.",
    ("last_name", "required"): "Nachname ist erforderlich.",
    ("birthday", "invalid_date"): "Geburtstag muss ein gültiges Datum sein.",
}
_MISSING_FORM_MESSAGE = (
    "Die Formulardaten sind unvollständig. Bitte Seite neu laden."
)
_UNKNOWN_FORM_MESSAGE = (
    "Die Formulardaten enthalten unbekannte Felder. Bitte Seite neu laden."
)


def _immutable_errors(errors):
    return MappingProxyType(
        {
            field: tuple(field_errors)
            for field, field_errors in errors.items()
        }
    )


def _error(status, code, field, field_code=None, message=None):
    field_code = field_code or code
    message = message or _MESSAGES.get(
        field_code,
        "Die Formulardaten sind ungültig.",
    )
    return KidEditParseError(
        status=status,
        code=code,
        errors=_immutable_errors(
            {field: (KidEditFieldError(field_code, message),)}
        ),
    )


def _validation_error(field, code, message=None):
    return _error(
        422,
        "validation_error",
        field,
        code,
        message or _FIELD_MESSAGES.get((field, code)),
    )


def _public_field_error(field, code):
    if code in {"control", "single_line"}:
        code = "invalid_type"
    label = _FIELD_LABELS[field]
    if code == "invalid_type":
        message = f"{label} hat ein ungültiges Format."
    elif code == "too_long":
        message = (
            f"{label} darf höchstens {_FIELD_LIMITS[field]} Zeichen lang sein."
        )
    else:
        message = _FIELD_MESSAGES.get(
            (field, code),
            _MESSAGES.get(code, "Der eingegebene Wert ist ungültig."),
        )
    return KidEditFieldError(code, message)


def _exact_keys(value, expected):
    if not isinstance(value, dict):
        return "invalid_type"
    actual = frozenset(value)
    expected = frozenset(expected)
    if expected - actual:
        return "missing_field"
    if actual - expected:
        return "unknown_field"
    return None


def _positive_integer(value):
    return type(value) is int and value > 0


def _nonnegative_integer(value):
    return type(value) is int and value >= 0


def _decode_request_id(value):
    if not isinstance(value, str):
        return None, "invalid_type"
    normalized = value.strip()
    if not normalized:
        return None, "required"
    if len(normalized) > 255:
        return None, "too_long"
    return normalized, None


def _decode_fields(values):
    normalized = {}
    errors = {}
    for field in FIELD_CONTRACTS:
        value = values[field.api_name]
        if isinstance(value, (list, dict)):
            errors[field.api_name] = (
                _public_field_error(field.api_name, "invalid_type"),
            )
            continue
        if has_legacy_token_syntax(value):
            if field.api_name in _LEGACY_FIELDS:
                normalized[field.api_name] = value
            else:
                errors[field.api_name] = (
                    _public_field_error(field.api_name, "invalid_type"),
                )
            continue
        try:
            canonical = canonicalize_submission_value(field, value)
        except KidEditContractError as error:
            if (
                field.api_name == "registrant_email"
                and error.code == "invalid_email"
            ):
                normalized[field.api_name] = value.strip()
                continue
            errors[field.api_name] = (
                _public_field_error(field.api_name, error.code),
            )
        else:
            normalized[field.api_name] = canonical.api_value
    if errors:
        return None, KidEditParseError(
            status=422,
            code="validation_error",
            errors=_immutable_errors(errors),
        )
    return MappingProxyType(normalized), None


def _decode_swp_target(value, field_name):
    if not isinstance(value, dict):
        return None, _validation_error(field_name, "invalid_type")
    kind = value.get("kind")
    if kind == "unassigned":
        shape_error = _exact_keys(value, {"kind"})
        if shape_error:
            return None, _validation_error(field_name, shape_error)
        return SwpTarget(kind="unassigned"), None
    if kind == "focus":
        shape_error = _exact_keys(value, {"kind", "focus_id"})
        if shape_error:
            return None, _validation_error(field_name, shape_error)
        if not _positive_integer(value["focus_id"]):
            return None, _validation_error(field_name, "invalid_type")
        return SwpTarget(kind="focus", focus_id=value["focus_id"]), None
    if kind == "preserve_legacy":
        shape_error = _exact_keys(value, {"kind", "token"})
        if shape_error:
            return None, _validation_error(field_name, shape_error)
        if not has_baseline_token_syntax(value["token"]):
            return None, _validation_error(field_name, "invalid_choice")
        return SwpTarget(
            kind="preserve_legacy",
            token=value["token"],
        ), None
    return None, _validation_error(field_name, "invalid_choice")


def _decode_swp(value):
    if not isinstance(value, list):
        return None, _validation_error("_form", "invalid_type")
    decoded = []
    seen = set()
    errors = {}
    for raw_item in value:
        if not isinstance(raw_item, dict):
            errors.setdefault("_form", []).append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
            continue
        period_id = raw_item.get("period_id")
        if not _positive_integer(period_id):
            errors.setdefault("_form", []).append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
            continue
        field_name = f"swp.{period_id}"
        shape_error = _exact_keys(
            raw_item,
            {"period_id", "baseline", "target"},
        )
        if shape_error:
            errors.setdefault(field_name, []).append(
                KidEditFieldError(shape_error, _MESSAGES[shape_error])
            )
            continue
        if period_id in seen:
            errors.setdefault(field_name, []).append(
                KidEditFieldError("duplicate_id", _MESSAGES["duplicate_id"])
            )
            continue
        seen.add(period_id)
        item_errors = []
        if not has_baseline_token_syntax(raw_item["baseline"]):
            item_errors.append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
        target, error = _decode_swp_target(raw_item["target"], field_name)
        if error:
            item_errors.extend(error.errors[field_name])
        if item_errors:
            errors.setdefault(field_name, []).extend(item_errors)
        else:
            decoded.append(SwpItem(period_id, raw_item["baseline"], target))
    if errors:
        ordered_errors = {}
        if "_form" in errors:
            ordered_errors["_form"] = errors.pop("_form")
        for field_name in sorted(
            errors,
            key=lambda name: int(name.removeprefix("swp.")),
        ):
            ordered_errors[field_name] = errors[field_name]
        return None, KidEditParseError(
            status=422,
            code="validation_error",
            errors=_immutable_errors(ordered_errors),
        )
    return tuple(sorted(decoded, key=lambda item: item.period_id)), None


def _decode_happy_cleaning_target(value, field_name):
    if not isinstance(value, dict):
        return None, _validation_error(field_name, "invalid_type")
    kind = value.get("kind")
    if kind in {"unassigned", "excused"}:
        shape_error = _exact_keys(value, {"kind"})
        if shape_error:
            return None, _validation_error(field_name, shape_error)
        return HappyCleaningTarget(kind=kind), None
    if kind == "station":
        shape_error = _exact_keys(value, {"kind", "station_id"})
        if shape_error:
            return None, _validation_error(field_name, shape_error)
        if not _positive_integer(value["station_id"]):
            return None, _validation_error(field_name, "invalid_type")
        return HappyCleaningTarget(
            kind="station",
            station_id=value["station_id"],
        ), None
    return None, _validation_error(field_name, "invalid_choice")


def _decode_happy_cleaning(value):
    if not isinstance(value, list):
        return None, _validation_error("_form", "invalid_type")
    decoded = []
    seen = set()
    errors = {}
    for raw_item in value:
        if not isinstance(raw_item, dict):
            errors.setdefault("_form", []).append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
            continue
        event_id = raw_item.get("event_id")
        if not _positive_integer(event_id):
            errors.setdefault("_form", []).append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
            continue
        field_name = f"happy_cleaning.{event_id}"
        shape_error = _exact_keys(
            raw_item,
            {"event_id", "expected_assignment_version", "target"},
        )
        if shape_error:
            errors.setdefault(field_name, []).append(
                KidEditFieldError(shape_error, _MESSAGES[shape_error])
            )
            continue
        if event_id in seen:
            errors.setdefault(field_name, []).append(
                KidEditFieldError("duplicate_id", _MESSAGES["duplicate_id"])
            )
            continue
        seen.add(event_id)
        item_errors = []
        version = raw_item["expected_assignment_version"]
        if not _nonnegative_integer(version):
            item_errors.append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )
        target, error = _decode_happy_cleaning_target(
            raw_item["target"],
            field_name,
        )
        if error:
            item_errors.extend(error.errors[field_name])
        if item_errors:
            errors.setdefault(field_name, []).extend(item_errors)
        else:
            decoded.append(HappyCleaningItem(event_id, version, target))
    if errors:
        ordered_errors = {}
        if "_form" in errors:
            ordered_errors["_form"] = errors.pop("_form")
        for field_name in sorted(
            errors,
            key=lambda name: int(name.removeprefix("happy_cleaning.")),
        ):
            ordered_errors[field_name] = errors[field_name]
        return None, KidEditParseError(
            status=422,
            code="validation_error",
            errors=_immutable_errors(ordered_errors),
        )
    return tuple(sorted(decoded, key=lambda item: item.event_id)), None


def decode_kid_edit_request(raw_body, content_type):
    """Decode syntax and values without authenticating baselines or state."""
    try:
        body_length = len(raw_body)
    except TypeError:
        body_length = 0
    if body_length > BODY_LIMIT:
        return _error(413, "request_too_large", "_form")
    if content_type != "application/json":
        return _error(415, "unsupported_media_type", "_form")
    if not isinstance(raw_body, bytes):
        return _error(400, "invalid_json", "_form")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "invalid_json", "_form")
    if not isinstance(payload, dict):
        return _error(400, "invalid_json", "_form")

    shape_error = _exact_keys(payload, _TOP_LEVEL_KEYS)
    if shape_error == "missing_field":
        return _validation_error(
            "_form",
            shape_error,
            _MISSING_FORM_MESSAGE,
        )
    if shape_error == "unknown_field":
        return _validation_error(
            "_form",
            shape_error,
            _UNKNOWN_FORM_MESSAGE,
        )

    for container_name in ("fields", "field_baselines"):
        shape_error = _exact_keys(payload[container_name], _FIELD_NAME_SET)
        if shape_error:
            return _validation_error("_form", shape_error)

    request_id, request_id_error = _decode_request_id(payload["request_id"])
    form_errors = []
    if request_id_error:
        form_errors.append(
            KidEditFieldError(
                request_id_error,
                _MESSAGES[request_id_error],
            )
        )
    for version_name in (
        "expected_edit_version",
        "expected_number_version",
    ):
        if not _positive_integer(payload[version_name]):
            form_errors.append(
                KidEditFieldError("invalid_type", _MESSAGES["invalid_type"])
            )

    baselines = {}
    baseline_errors = {}
    for field_name in _FIELD_NAMES:
        baseline = payload["field_baselines"][field_name]
        if not has_baseline_token_syntax(baseline):
            baseline_errors[field_name] = (
                _public_field_error(field_name, "invalid_type"),
            )
        else:
            baselines[field_name] = baseline

    fields, fields_error = _decode_fields(payload["fields"])
    swp, swp_error = _decode_swp(payload["swp"])

    number = payload["happy_cleaning_number"]
    number_error = None
    if number is not None and (
        not _positive_integer(number)
        or number > HAPPY_CLEANING_NUMBER_CONTRACT.maximum
    ):
        number_error = KidEditFieldError(
            "invalid_number",
            _MESSAGES["invalid_number"],
        )

    happy_cleaning, happy_cleaning_error = _decode_happy_cleaning(
        payload["happy_cleaning"]
    )
    for dynamic_error in (swp_error, happy_cleaning_error):
        if dynamic_error is not None and "_form" in dynamic_error.errors:
            form_errors.extend(dynamic_error.errors["_form"])

    combined = {}
    if form_errors:
        combined["_form"] = form_errors
    for field_name in _FIELD_NAMES:
        field_errors = []
        field_errors.extend(baseline_errors.get(field_name, ()))
        if fields_error is not None:
            field_errors.extend(fields_error.errors.get(field_name, ()))
        if field_errors:
            combined[field_name] = field_errors
    if swp_error is not None:
        for field_name, field_errors in swp_error.errors.items():
            if field_name != "_form":
                combined[field_name] = list(field_errors)
    if number_error is not None:
        combined["happy_cleaning_number"] = [number_error]
    if happy_cleaning_error is not None:
        for field_name, field_errors in happy_cleaning_error.errors.items():
            if field_name != "_form":
                combined[field_name] = list(field_errors)
    if combined:
        return KidEditParseError(
            status=422,
            code="validation_error",
            errors=_immutable_errors(combined),
        )
    return KidEditRequest(
        request_id=request_id,
        expected_edit_version=payload["expected_edit_version"],
        field_baselines=MappingProxyType(baselines),
        fields=fields,
        swp=swp,
        happy_cleaning_number=number,
        expected_number_version=payload["expected_number_version"],
        happy_cleaning=happy_cleaning,
    )
