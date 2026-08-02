"""Schema and canonical values for the kid-edit contract."""

from dataclasses import dataclass
from datetime import date
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from budo_app.text_cleaning import (
    DEFAULT_EMPTY_VALUES,
    FOOD_EMPTY_VALUES,
    REQUEST_EMPTY_VALUES,
)


@dataclass(frozen=True, slots=True)
class FieldContract:
    api_name: str
    storage_name: str
    value_type: str
    max_length: int | None = None
    multiline: bool = False
    required: bool = False
    semantic_blanks: frozenset = frozenset()
    clear_storage_value: object = None
    api_to_storage: tuple = ()


@dataclass(frozen=True, slots=True)
class IntegerFieldContract:
    api_name: str
    storage_name: str
    value_type: str
    minimum: int
    maximum: int
    required: bool = False


@dataclass(frozen=True, slots=True)
class CanonicalizedValue:
    api_value: object
    storage_value: object
    preserve_raw: bool = False
    legacy_kind: str | None = None


class KidEditContractError(Exception):
    """Neutral validation failure at the kid-edit contract boundary."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _field(
    api_name,
    storage_name,
    value_type,
    *,
    max_length=None,
    multiline=False,
    required=False,
    semantic_blanks=frozenset(),
    clear_storage_value=None,
    api_to_storage=(),
):
    return FieldContract(
        api_name=api_name,
        storage_name=storage_name,
        value_type=value_type,
        max_length=max_length,
        multiline=multiline,
        required=required,
        semantic_blanks=frozenset(semantic_blanks),
        clear_storage_value=clear_storage_value,
        api_to_storage=tuple(api_to_storage),
    )


FIELD_CONTRACTS = (
    _field("first_name", "kid_vorname", "text", max_length=255, required=True),
    _field("last_name", "kid_nachname", "text", max_length=255, required=True),
    _field(
        "sex",
        "sex",
        "enum",
        semantic_blanks={"", "-", "nan", "none"},
        api_to_storage=(
            ("female", "weiblich"),
            ("male", "männlich"),
            ("diverse", "divers"),
        ),
    ),
    _field("birthday", "kid_birthday", "date"),
    _field(
        "stay_weeks",
        "turnus_dauer",
        "integer",
        api_to_storage=((1, 1), (2, 2)),
    ),
    _field(
        "siblings",
        "geschwister",
        "text",
        max_length=255,
        semantic_blanks=REQUEST_EMPTY_VALUES,
    ),
    _field(
        "tent_request",
        "zeltwunsch",
        "text",
        max_length=255,
        multiline=True,
        semantic_blanks=REQUEST_EMPTY_VALUES,
    ),
    _field("budo_experience", "budo_erfahrung", "boolean"),
    _field(
        "social_security_number",
        "sozialversicherungsnr",
        "text",
        max_length=255,
    ),
    _field(
        "illness",
        "illness",
        "text",
        max_length=10_000,
        multiline=True,
        semantic_blanks=DEFAULT_EMPTY_VALUES,
    ),
    _field(
        "drugs",
        "drugs",
        "text",
        max_length=10_000,
        multiline=True,
        semantic_blanks=DEFAULT_EMPTY_VALUES,
    ),
    _field(
        "vegetarian",
        "vegetarisch",
        "enum",
        semantic_blanks={"", "-", "nan", "none"},
        api_to_storage=((True, "ja"), (False, "nein")),
    ),
    _field(
        "special_food",
        "special_food_description",
        "text",
        max_length=255,
        multiline=True,
        semantic_blanks=FOOD_EMPTY_VALUES,
    ),
    _field("swimmer", "swimmer", "text", max_length=255),
    _field("consent", "einverstaendnis_erklaerung", "boolean"),
    _field(
        "over_the_counter_medication",
        "rezeptfreie_medikamente",
        "text",
        max_length=10_000,
        multiline=True,
    ),
    _field(
        "prescription_medication",
        "rezept_medikamente",
        "text",
        max_length=255,
        multiline=True,
    ),
    _field("tetanus", "tetanusimpfung", "text", max_length=255),
    _field("tick_vaccine", "zeckenimpfung", "text", max_length=255),
    _field("organization", "anmelde_organisation", "text", max_length=255),
    _field(
        "registrant_first_name",
        "anmelder_vorname",
        "text",
        max_length=255,
        clear_storage_value="",
    ),
    _field(
        "registrant_last_name",
        "anmelder_nachname",
        "text",
        max_length=255,
        clear_storage_value="",
    ),
    _field("registrant_email", "anmelder_email", "email", max_length=255),
    _field("registrant_phone", "anmelder_mobil", "text", max_length=255),
    _field("insured_with", "hauptversichert_bei", "text", max_length=255),
    _field(
        "emergency_contacts",
        "notfall_kontakte",
        "text",
        max_length=10_000,
        multiline=True,
    ),
    _field(
        "budo_family",
        "budo_family",
        "enum",
        semantic_blanks={""},
        api_to_storage=(("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL")),
    ),
)


HAPPY_CLEANING_NUMBER_CONTRACT = IntegerFieldContract(
    api_name="happy_cleaning_number",
    storage_name="happy_cleaning_number",
    value_type="integer",
    minimum=1,
    maximum=2_147_483_647,
)


FIELD_CONTRACTS_BY_STORAGE_NAME = {
    field.storage_name: field for field in FIELD_CONTRACTS
}


_STRICT_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


def _normalized_text(value):
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _validate_text(field, value):
    if not isinstance(value, str):
        raise KidEditContractError("invalid_type")
    normalized_line_endings = value.replace("\r\n", "\n").replace(
        "\r",
        "\n",
    )
    for character in normalized_line_endings:
        if ord(character) < 32 and character not in {"\n", "\t"}:
            raise KidEditContractError("control")
    normalized = normalized_line_endings.strip()
    if not field.multiline and ("\n" in normalized or "\t" in normalized):
        raise KidEditContractError("single_line")
    if field.max_length is not None and len(normalized) > field.max_length:
        raise KidEditContractError("too_long")
    return normalized


def _is_semantic_blank(field, normalized):
    return normalized.casefold() in field.semantic_blanks


def _clear_value(field):
    return CanonicalizedValue(
        api_value="" if field.value_type in {"text", "email"} else None,
        storage_value=field.clear_storage_value,
    )


def _matching_storage_choice(field, raw_value):
    if isinstance(raw_value, str):
        normalized = _normalized_text(raw_value)
        for api_value, storage_value in field.api_to_storage:
            if (
                isinstance(storage_value, str)
                and (
                    normalized == storage_value
                    if field.api_name == "budo_family"
                    else normalized.casefold() == storage_value.casefold()
                )
            ):
                return True, api_value, normalized
        return False, normalized, normalized
    for api_value, storage_value in field.api_to_storage:
        if type(raw_value) is type(storage_value) and raw_value == storage_value:
            return True, api_value, raw_value
    return False, raw_value, raw_value


def canonicalize_storage_value(field, raw_value):
    """Expose canonical API meaning while retaining the exact stored value."""
    if raw_value is None:
        api_value = "" if field.value_type in {"text", "email"} else None
        return CanonicalizedValue(api_value, raw_value)

    if field.value_type in {"text", "email"}:
        if not isinstance(raw_value, str):
            return CanonicalizedValue(
                raw_value,
                raw_value,
                preserve_raw=True,
                legacy_kind="invalid_type",
            )
        normalized = _normalized_text(raw_value)
        if _is_semantic_blank(field, normalized):
            return CanonicalizedValue("", raw_value)
        if field.value_type == "email" and normalized:
            try:
                validate_email(normalized)
            except ValidationError:
                return CanonicalizedValue(
                    normalized,
                    raw_value,
                    preserve_raw=True,
                    legacy_kind="invalid_email",
                )
        return CanonicalizedValue(normalized, raw_value)

    if field.value_type in {"enum", "integer"}:
        if isinstance(raw_value, str) and _is_semantic_blank(
            field,
            _normalized_text(raw_value),
        ):
            return CanonicalizedValue(None, raw_value)
        matched, api_value, _normalized = _matching_storage_choice(
            field,
            raw_value,
        )
        if matched:
            return CanonicalizedValue(api_value, raw_value)
        return CanonicalizedValue(
            api_value,
            raw_value,
            preserve_raw=True,
            legacy_kind="unknown_choice",
        )

    if field.value_type == "boolean":
        if type(raw_value) is bool:
            return CanonicalizedValue(raw_value, raw_value)
        return CanonicalizedValue(
            raw_value,
            raw_value,
            preserve_raw=True,
            legacy_kind="unknown_choice",
        )

    if field.value_type == "date":
        if isinstance(raw_value, date):
            return CanonicalizedValue(raw_value.isoformat(), raw_value)
        return CanonicalizedValue(
            raw_value,
            raw_value,
            preserve_raw=True,
            legacy_kind="invalid_date",
        )

    raise KidEditContractError("invalid_contract")


def _canonicalize_text_submission(field, value):
    normalized = _validate_text(field, value)
    if _is_semantic_blank(field, normalized):
        normalized = ""
    if field.required and not normalized:
        raise KidEditContractError("required")
    if not normalized:
        return _clear_value(field)
    if field.value_type == "email":
        try:
            validate_email(normalized)
        except ValidationError:
            raise KidEditContractError("invalid_email") from None
    return CanonicalizedValue(normalized, normalized)


def canonicalize_submission_value(field, api_value):
    """Validate and normalize one API value into its database representation."""
    if field.value_type in {"text", "email"}:
        return _canonicalize_text_submission(field, api_value)

    if field.value_type == "boolean":
        if api_value is None and not field.required:
            return CanonicalizedValue(None, None)
        if type(api_value) is not bool:
            raise KidEditContractError("invalid_type")
        return CanonicalizedValue(api_value, api_value)

    if field.value_type == "date":
        if api_value is None and not field.required:
            return CanonicalizedValue(None, None)
        if not isinstance(api_value, str):
            raise KidEditContractError("invalid_type")
        if not _STRICT_DATE.fullmatch(api_value):
            raise KidEditContractError("invalid_date")
        try:
            parsed = date.fromisoformat(api_value)
        except ValueError:
            raise KidEditContractError("invalid_date") from None
        return CanonicalizedValue(parsed.isoformat(), parsed)

    if field.value_type == "integer":
        if api_value is None and not field.required:
            return CanonicalizedValue(None, None)
        if isinstance(api_value, bool) or not isinstance(api_value, int):
            raise KidEditContractError("invalid_type")
    elif field.value_type == "enum":
        if api_value is None and not field.required:
            return CanonicalizedValue(None, field.clear_storage_value)
    else:
        raise KidEditContractError("invalid_contract")

    for choice, storage_value in field.api_to_storage:
        if type(api_value) is type(choice) and api_value == choice:
            return CanonicalizedValue(api_value, storage_value)
    raise KidEditContractError("invalid_choice")


def _legacy_comparison_value(field, submitted_value):
    if field.value_type in {"text", "email", "enum"} and isinstance(
        submitted_value,
        str,
    ):
        return _normalized_text(submitted_value)
    return submitted_value


def is_canonical_no_op(field, raw_storage_value, submitted_api_value):
    """Compare meanings without rewriting canonically equivalent raw storage."""
    current = canonicalize_storage_value(field, raw_storage_value)
    try:
        submitted = canonicalize_submission_value(field, submitted_api_value)
    except KidEditContractError:
        return (
            current.preserve_raw
            and _legacy_comparison_value(field, submitted_api_value)
            == current.api_value
        )
    return submitted.api_value == current.api_value


from .signing import (  # noqa: E402
    sign_field_baseline,
    sign_legacy_preserve_value,
    sign_swp_baseline,
    verify_field_baseline,
    verify_legacy_preserve_value,
    verify_swp_baseline,
)
from .decoder import KidEditParseError, decode_kid_edit_request  # noqa: E402
from .validation import (  # noqa: E402
    KidEditCurrentHappyCleaningEvent,
    KidEditCurrentHappyCleaningTarget,
    KidEditCurrentState,
    KidEditCurrentSwpPeriod,
    KidEditValidationError,
    validate_kid_edit_command,
)


__all__ = (
    "FIELD_CONTRACTS",
    "HAPPY_CLEANING_NUMBER_CONTRACT",
    "KidEditContractError",
    "canonicalize_storage_value",
    "canonicalize_submission_value",
    "is_canonical_no_op",
    "sign_field_baseline",
    "verify_field_baseline",
    "sign_swp_baseline",
    "verify_swp_baseline",
    "sign_legacy_preserve_value",
    "verify_legacy_preserve_value",
    "KidEditParseError",
    "decode_kid_edit_request",
    "KidEditCurrentState",
    "KidEditCurrentSwpPeriod",
    "KidEditCurrentHappyCleaningEvent",
    "KidEditCurrentHappyCleaningTarget",
    "KidEditValidationError",
    "validate_kid_edit_command",
)
