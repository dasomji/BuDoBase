"""Opaque, digest-only signatures for kid-edit baseline state."""

import base64
import hashlib
import hmac
import json
import re
import secrets

from django.conf import settings

from . import FIELD_CONTRACTS


_ORDINARY_TOKEN = re.compile(r"\Av1\.([A-Za-z0-9_-]{43})\Z")
_LEGACY_TOKEN = re.compile(r"\Alegacy:v1\.([A-Za-z0-9_-]{43})\Z")
_FIELD_NAMES = frozenset(field.api_name for field in FIELD_CONTRACTS)


def _positive_id(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _field_name(value):
    if not isinstance(value, str):
        raise TypeError("field_name must be text")
    if value not in _FIELD_NAMES:
        raise ValueError("field_name is not in the kid-edit contract")
    return value


def _typed_value(value):
    if value is None:
        return ("null",)
    if type(value) is bool:
        return ("boolean", value)
    if type(value) is int:
        return ("integer", str(value))
    if type(value) is str:
        return ("text", value)
    raise TypeError("signed values must be null, text, boolean, or integer")


def _focus_ids(value):
    if not isinstance(value, tuple):
        raise TypeError("current_focus_ids must be a tuple")
    previous = 0
    for focus_id in value:
        _positive_id(focus_id, "focus_id")
        if focus_id <= previous:
            raise ValueError(
                "current_focus_ids must be strictly increasing and unique"
            )
        previous = focus_id
    return value


def _payload(*parts):
    return json.dumps(
        ("kid-edit-contract", "v1", *parts),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _field_payload(*, turnus_id, child_id, field_name, canonical_value):
    return _payload(
        "field-baseline",
        _positive_id(turnus_id, "turnus_id"),
        _positive_id(child_id, "child_id"),
        _field_name(field_name),
        _typed_value(canonical_value),
    )


def _swp_payload(*, turnus_id, child_id, period_id, current_focus_ids):
    return _payload(
        "swp-baseline",
        _positive_id(turnus_id, "turnus_id"),
        _positive_id(child_id, "child_id"),
        _positive_id(period_id, "period_id"),
        _focus_ids(current_focus_ids),
    )


def _legacy_payload(*, turnus_id, child_id, field_name, raw_storage_value):
    return _payload(
        "legacy-preserve",
        _positive_id(turnus_id, "turnus_id"),
        _positive_id(child_id, "child_id"),
        _field_name(field_name),
        _typed_value(raw_storage_value),
    )


def _digest(payload, key):
    digest = hmac.new(
        str(key).encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _sign(payload, *, legacy=False):
    prefix = "legacy:v1." if legacy else "v1."
    return prefix + _digest(payload, settings.SECRET_KEY)


def _token_digest(token, *, legacy):
    if not isinstance(token, str):
        return None
    ordinary_token = str(token)
    pattern = _LEGACY_TOKEN if legacy else _ORDINARY_TOKEN
    match = pattern.fullmatch(ordinary_token)
    return None if match is None else match.group(1)


def has_baseline_token_syntax(token):
    return _token_digest(token, legacy=False) is not None


def has_legacy_token_syntax(token):
    return _token_digest(token, legacy=True) is not None


def _verify(token, payload, *, legacy=False):
    supplied_digest = _token_digest(token, legacy=legacy)
    if supplied_digest is None:
        return False
    keys = (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS)
    matched = False
    for key in keys:
        matched |= secrets.compare_digest(supplied_digest, _digest(payload, key))
    return bool(matched)


def sign_field_baseline(
    *,
    turnus_id,
    child_id,
    field_name,
    canonical_value,
):
    return _sign(
        _field_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            field_name=field_name,
            canonical_value=canonical_value,
        )
    )


def verify_field_baseline(
    token,
    *,
    turnus_id,
    child_id,
    field_name,
    canonical_value,
):
    try:
        payload = _field_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            field_name=field_name,
            canonical_value=canonical_value,
        )
    except (TypeError, ValueError):
        return False
    return _verify(token, payload)


def sign_swp_baseline(
    *,
    turnus_id,
    child_id,
    period_id,
    current_focus_ids,
):
    return _sign(
        _swp_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            period_id=period_id,
            current_focus_ids=current_focus_ids,
        )
    )


def verify_swp_baseline(
    token,
    *,
    turnus_id,
    child_id,
    period_id,
    current_focus_ids,
):
    try:
        payload = _swp_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            period_id=period_id,
            current_focus_ids=current_focus_ids,
        )
    except (TypeError, ValueError):
        return False
    return _verify(token, payload)


def sign_legacy_preserve_value(
    *,
    turnus_id,
    child_id,
    field_name,
    raw_storage_value,
):
    return _sign(
        _legacy_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            field_name=field_name,
            raw_storage_value=raw_storage_value,
        ),
        legacy=True,
    )


def verify_legacy_preserve_value(
    token,
    *,
    turnus_id,
    child_id,
    field_name,
    raw_storage_value,
):
    try:
        payload = _legacy_payload(
            turnus_id=turnus_id,
            child_id=child_id,
            field_name=field_name,
            raw_storage_value=raw_storage_value,
        )
    except (TypeError, ValueError):
        return False
    return _verify(token, payload, legacy=True)
