"""Dedicated canonical HMAC fingerprints for validated kid-edit commands."""

from datetime import date
import hashlib
import hmac
import json
import re
import secrets

from django.conf import settings


KID_EDIT_FINGERPRINT_SALT = "budo.kid-edit.command-fingerprint.v1"
_FINGERPRINT = re.compile(r"\Ahmac-sha256:v1:([0-9a-f]{64})\Z")


def _typed(value):
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["boolean", value]
    if type(value) is int:
        return ["integer", str(value)]
    if type(value) is str:
        return ["text", value]
    if type(value) is date:
        return ["date", value.isoformat()]
    raise TypeError("Unsupported kid-edit command value.")


def _swp_target(target):
    return {
        "kind": target.kind,
        "focus_id": _typed(target.focus_id),
        "token": _typed(target.token),
    }


def _happy_cleaning_target(target):
    return {
        "kind": target.kind,
        "station_id": _typed(target.station_id),
    }


def _command_payload(command):
    value = {
        "request_id": _typed(command.request_id),
        "turnus_id": _typed(command.turnus_id),
        "child_id": _typed(command.child_id),
        "expected_edit_version": _typed(command.expected_edit_version),
        "storage_fields": [
            [name, _typed(field_value)]
            for name, field_value in sorted(command.storage_fields.items())
        ],
        "swp": [
            {
                "period_id": _typed(item.period_id),
                "current_focus_ids": [
                    _typed(focus_id)
                    for focus_id in sorted(item.current_focus_ids)
                ],
                "target": _swp_target(item.target),
            }
            for item in sorted(command.swp, key=lambda item: item.period_id)
        ],
        "happy_cleaning_number": _typed(command.happy_cleaning_number),
        "expected_number_version": _typed(command.expected_number_version),
        "happy_cleaning": [
            {
                "event_id": _typed(item.event_id),
                "current_assignment_version": _typed(
                    item.current_assignment_version
                ),
                "target": _happy_cleaning_target(item.target),
            }
            for item in sorted(
                command.happy_cleaning,
                key=lambda item: item.event_id,
            )
        ],
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _request_payload(request, *, turnus_id, child_id):
    """Canonicalize decoded request intent before mutable state is loaded."""
    value = {
        "request_id": _typed(request.request_id),
        "turnus_id": _typed(turnus_id),
        "child_id": _typed(child_id),
        "expected_edit_version": _typed(request.expected_edit_version),
        "field_baselines": [
            [name, _typed(value)]
            for name, value in sorted(request.field_baselines.items())
        ],
        "fields": [
            [name, _typed(value)]
            for name, value in sorted(request.fields.items())
        ],
        "swp": [
            {
                "period_id": _typed(item.period_id),
                "baseline": _typed(item.baseline),
                "target": _swp_target(item.target),
            }
            for item in sorted(request.swp, key=lambda item: item.period_id)
        ],
        "happy_cleaning_number": _typed(request.happy_cleaning_number),
        "expected_number_version": _typed(request.expected_number_version),
        "happy_cleaning": [
            {
                "event_id": _typed(item.event_id),
                "expected_assignment_version": _typed(
                    item.expected_assignment_version
                ),
                "target": _happy_cleaning_target(item.target),
            }
            for item in sorted(
                request.happy_cleaning, key=lambda item: item.event_id,
            )
        ],
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(command, key):
    payload = _command_payload(command)
    return hmac.new(
        str(key).encode("utf-8"),
        KID_EDIT_FINGERPRINT_SALT.encode("ascii") + b"\0" + payload,
        hashlib.sha256,
    ).hexdigest()


def _request_digest(request, *, turnus_id, child_id, key):
    payload = _request_payload(
        request, turnus_id=turnus_id, child_id=child_id,
    )
    return hmac.new(
        str(key).encode("utf-8"),
        KID_EDIT_FINGERPRINT_SALT.encode("ascii") + b"\0request\0" + payload,
        hashlib.sha256,
    ).hexdigest()


def sign_kid_edit_command(command):
    return f"hmac-sha256:v1:{_digest(command, settings.SECRET_KEY)}"


def verify_kid_edit_command_fingerprint(fingerprint, command):
    if type(fingerprint) is not str:
        return False
    match = _FINGERPRINT.fullmatch(fingerprint)
    if match is None:
        return False
    supplied = match.group(1)
    matched = False
    for key in (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS):
        matched |= secrets.compare_digest(supplied, _digest(command, key))
    return bool(matched)


def sign_kid_edit_request(request, *, turnus_id, child_id):
    return "hmac-sha256:v1:" + _request_digest(
        request,
        turnus_id=turnus_id,
        child_id=child_id,
        key=settings.SECRET_KEY,
    )


def verify_kid_edit_request_fingerprint(
    fingerprint, request, *, turnus_id, child_id,
):
    if type(fingerprint) is not str:
        return False
    match = _FINGERPRINT.fullmatch(fingerprint)
    if match is None:
        return False
    supplied = match.group(1)
    matched = False
    for key in (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS):
        matched |= secrets.compare_digest(
            supplied,
            _request_digest(
                request,
                turnus_id=turnus_id,
                child_id=child_id,
                key=key,
            ),
        )
    return bool(matched)
