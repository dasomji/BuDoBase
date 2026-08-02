"""Validation for the storage-faithful ``budo.kid-edit`` audit schema."""

from datetime import date
import json
import re

from django.core.exceptions import ValidationError

from budo_app.kid_edit_contracts import FIELD_CONTRACTS
from budo_app.kid_edit_contracts.signing import (
    has_baseline_token_syntax,
    has_legacy_token_syntax,
)
from budo_app.models import Kinder

MAX_KID_EDIT_AUDIT_BYTES = 4 * 1024 * 1024
POSTGRES_INTEGER_MIN = -2_147_483_648
POSTGRES_INTEGER_MAX = 2_147_483_647
POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807

# Storage values retain an audit schema independent of canonical API values.
# Tuple values are kind, nullable, max length; the roster follows FIELD_CONTRACTS.
_STORAGE_KIND_BY_VALUE_TYPE = {
    "boolean": "boolean",
    "date": "date",
    "email": "string",
    "enum": "string",
    "integer": "integer",
    "text": "string",
}


def _storage_field_schema(field):
    model_field = Kinder._meta.get_field(field.storage_name)
    maximum = (
        field.max_length
        if field.max_length is not None
        else model_field.max_length
    )
    return (
        _STORAGE_KIND_BY_VALUE_TYPE[field.value_type],
        model_field.null,
        maximum,
    )


_STORAGE_FIELDS = {
    field.api_name: _storage_field_schema(field)
    for field in FIELD_CONTRACTS
}

_TOP_KEYS = {
    "schema", "version", "result", "changed_paths", "before", "after",
}
_SNAPSHOT_KEYS = {
    "versions", "fields", "happy_cleaning_number", "swp", "happy_cleaning",
}
_VERSION_KEYS = {"edit", "happy_cleaning_number"}
_PERIOD_KEYS = {
    "period_id", "period_code", "period_label", "start", "duration_days",
    "focuses",
}
_FOCUS_KEYS = {"id", "label"}
_EVENT_KEYS = {
    "event_id", "display_number", "event_label", "event_revision",
    "assignment_version", "target",
}
_STRICT_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_SUMMARY_RELATIONSHIP_PATH = re.compile(
    r"\A(?:swp|happy_cleaning)\.([1-9]\d*)\Z"
)


def _invalid(message="Invalid kid-edit audit details."):
    raise ValidationError({"details": message})


def validate_kid_edit_summary(schema, version, result, changed_paths):
    """Validate the independently projected, list-safe v1 summary fields."""
    if (
        schema != "budo.kid-edit"
        or type(version) is not int
        or version != 1
        or result != "updated"
        or type(changed_paths) is not list
        or not changed_paths
        or any(type(path) is not str for path in changed_paths)
        or len(changed_paths) != len(set(changed_paths))
    ):
        _invalid()
    static_paths = set(_STORAGE_FIELDS) | {"happy_cleaning_number"}
    for path in changed_paths:
        if path in static_paths:
            continue
        match = _SUMMARY_RELATIONSHIP_PATH.fullmatch(path)
        if match is None or int(match.group(1)) > POSTGRES_BIGINT_MAX:
            _invalid()
    return {
        "schema": schema,
        "version": version,
        "result": result,
        "changed_paths": list(changed_paths),
    }


def _plain_json(value, *, depth=0):
    if depth > 8:
        _invalid()
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is list:
        return [_plain_json(item, depth=depth + 1) for item in value]
    if type(value) is dict:
        result = {}
        for key, item in value.items():
            if type(key) is not str:
                _invalid()
            result[key] = _plain_json(item, depth=depth + 1)
        return result
    _invalid()


def _require_keys(value, expected):
    if type(value) is not dict or set(value) != expected:
        _invalid()


def _positive_integer(value, *, maximum=POSTGRES_INTEGER_MAX):
    if type(value) is not int or value <= 0 or value > maximum:
        _invalid()
    return value


def _nonnegative_integer(value):
    if (
        type(value) is not int
        or value < 0
        or value > POSTGRES_INTEGER_MAX
    ):
        _invalid()
    return value


def _text(value, maximum, *, nullable=False, required=False):
    if nullable and value is None:
        return None
    if type(value) is not str or len(value) > maximum:
        _invalid()
    if required and not value:
        _invalid()
    if (
        has_baseline_token_syntax(value)
        or has_legacy_token_syntax(value)
    ):
        _invalid()
    return value


def _date(value, *, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or not _STRICT_DATE.fullmatch(value):
        _invalid()
    try:
        date.fromisoformat(value)
    except ValueError:
        _invalid()
    return value


def _field_value(name, value):
    kind, nullable, maximum = _STORAGE_FIELDS[name]
    if value is None:
        if not nullable:
            _invalid()
        return None
    if kind == "boolean":
        if type(value) is not bool:
            _invalid()
        return value
    if kind == "integer":
        if (
            type(value) is not int
            or value < POSTGRES_INTEGER_MIN
            or value > POSTGRES_INTEGER_MAX
        ):
            _invalid()
        return value
    if kind == "date":
        return _date(value, nullable=nullable)
    return _text(value, maximum)


def _fields(value):
    names = tuple(_STORAGE_FIELDS)
    _require_keys(value, set(names))
    return {
        name: _field_value(name, value[name])
        for name in names
    }


def _focus(value):
    _require_keys(value, _FOCUS_KEYS)
    return {
        "id": _positive_integer(
            value["id"],
            maximum=POSTGRES_BIGINT_MAX,
        ),
        "label": _text(value["label"], 255),
    }


def _period(value):
    _require_keys(value, _PERIOD_KEYS)
    if type(value["focuses"]) is not list:
        _invalid()
    focuses = [_focus(focus) for focus in value["focuses"]]
    focus_ids = [focus["id"] for focus in focuses]
    if len(focus_ids) != len(set(focus_ids)):
        _invalid()
    if focuses != sorted(
        focuses,
        key=lambda focus: (focus["label"].casefold(), focus["id"]),
    ):
        _invalid()
    return {
        "period_id": _positive_integer(
            value["period_id"],
            maximum=POSTGRES_BIGINT_MAX,
        ),
        "period_code": _text(value["period_code"], 2),
        "period_label": _text(value["period_label"], 255, required=True),
        "start": _date(value["start"]),
        "duration_days": _positive_integer(value["duration_days"]),
        "focuses": focuses,
    }


def _target(value, assignment_version):
    if type(value) is not dict or type(value.get("kind")) is not str:
        _invalid()
    kind = value["kind"]
    if kind == "unassigned":
        _require_keys(value, {"kind"})
        if assignment_version != 0:
            _invalid()
        return {"kind": kind}
    if assignment_version == 0:
        _invalid()
    if kind == "excused":
        _require_keys(value, {"kind"})
        return {"kind": kind}
    if kind == "station":
        _require_keys(value, {"kind", "station_id", "station_label"})
        return {
            "kind": kind,
            "station_id": _positive_integer(
                value["station_id"],
                maximum=POSTGRES_BIGINT_MAX,
            ),
            "station_label": _text(
                value["station_label"],
                255,
            ),
        }
    _invalid()


def _event(value):
    _require_keys(value, _EVENT_KEYS)
    assignment_version = _nonnegative_integer(value["assignment_version"])
    return {
        "event_id": _positive_integer(
            value["event_id"],
            maximum=POSTGRES_BIGINT_MAX,
        ),
        "display_number": _positive_integer(value["display_number"]),
        "event_label": _text(value["event_label"], 255, required=True),
        "event_revision": _positive_integer(value["event_revision"]),
        "assignment_version": assignment_version,
        "target": _target(value["target"], assignment_version),
    }


def _ordered_unique(items, *, identity, order):
    identities = [identity(item) for item in items]
    if len(identities) != len(set(identities)):
        _invalid()
    if items != sorted(items, key=order):
        _invalid()


def _snapshot(value):
    _require_keys(value, _SNAPSHOT_KEYS)
    _require_keys(value["versions"], _VERSION_KEYS)
    versions = {
        "edit": _positive_integer(value["versions"]["edit"]),
        "happy_cleaning_number": _positive_integer(
            value["versions"]["happy_cleaning_number"]
        ),
    }
    number = value["happy_cleaning_number"]
    if number is not None:
        number = _positive_integer(number)
    if type(value["swp"]) is not list or type(value["happy_cleaning"]) is not list:
        _invalid()
    periods = [_period(period) for period in value["swp"]]
    events = [_event(event) for event in value["happy_cleaning"]]
    _ordered_unique(
        periods,
        identity=lambda period: period["period_id"],
        order=lambda period: (period["start"], period["period_id"]),
    )
    _ordered_unique(
        events,
        identity=lambda event: event["event_id"],
        order=lambda event: (event["display_number"], event["event_id"]),
    )
    return {
        "versions": versions,
        "fields": _fields(value["fields"]),
        "happy_cleaning_number": number,
        "swp": periods,
        "happy_cleaning": events,
    }


def _validate_matching_configuration(before, after):
    before_periods = [
        (
            period["period_id"], period["period_code"],
            period["period_label"], period["start"], period["duration_days"],
        )
        for period in before["swp"]
    ]
    after_periods = [
        (
            period["period_id"], period["period_code"],
            period["period_label"], period["start"], period["duration_days"],
        )
        for period in after["swp"]
    ]
    before_events = [
        (event["event_id"], event["display_number"], event["event_label"])
        for event in before["happy_cleaning"]
    ]
    after_events = [
        (event["event_id"], event["display_number"], event["event_label"])
        for event in after["happy_cleaning"]
    ]
    if before_periods != after_periods or before_events != after_events:
        _invalid()


def _changed_paths(value, before):
    if type(value) is not list or not value:
        _invalid()
    canonical = list(_STORAGE_FIELDS)
    canonical.extend(
        f"swp.{period['period_id']}" for period in before["swp"]
    )
    canonical.append("happy_cleaning_number")
    canonical.extend(
        f"happy_cleaning.{event['event_id']}"
        for event in before["happy_cleaning"]
    )
    ranks = {path: index for index, path in enumerate(canonical)}
    if (
        any(type(path) is not str or path not in ranks for path in value)
        or len(value) != len(set(value))
        or value != sorted(value, key=ranks.__getitem__)
    ):
        _invalid()
    return list(value)


def validate_kid_edit_details(details, *, expected_changed_paths=None):
    """Return a fresh plain-JSON v1 detail object or raise ValidationError."""
    plain = _plain_json(details)
    try:
        encoded = json.dumps(
            plain,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        _invalid()
    if len(encoded) > MAX_KID_EDIT_AUDIT_BYTES:
        _invalid("Kid-edit audit details are too large.")

    _require_keys(plain, _TOP_KEYS)
    if (
        plain["schema"] != "budo.kid-edit"
        or type(plain["version"]) is not int
        or plain["version"] != 1
        or plain["result"] != "updated"
    ):
        _invalid()
    before = _snapshot(plain["before"])
    after = _snapshot(plain["after"])
    _validate_matching_configuration(before, after)
    changed_paths = _changed_paths(plain["changed_paths"], before)
    if expected_changed_paths is not None and (
        type(expected_changed_paths) not in {list, tuple}
        or any(type(path) is not str for path in expected_changed_paths)
        or tuple(changed_paths) != tuple(expected_changed_paths)
    ):
        _invalid()
    return {
        "schema": "budo.kid-edit",
        "version": 1,
        "result": "updated",
        "changed_paths": changed_paths,
        "before": before,
        "after": after,
    }
