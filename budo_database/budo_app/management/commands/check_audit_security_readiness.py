"""Lint the repository audit-security readiness manifest."""

from datetime import date
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


CONTROL_NAMES = frozenset({
    "storage_encryption",
    "database_transport",
    "browser_transport",
    "credentials_and_mfa",
    "logging_exclusions",
    "backup_and_export_handling",
    "permission_assignments",
    "restore_and_deletion_reconciliation",
    "incident_response",
})
TOP_LEVEL_KEYS = frozenset({
    "schema_version", "status", "reviewed_on", "candidate_preflight",
    "qa_preflight", "controls", "blockers", "at_rest_decision", "approval",
})
PREFLIGHT_KEYS = frozenset({
    "status", "environment", "provenance", "checked_on", "checked",
    "supported", "unsupported", "total_bytes", "max_bytes", "limit_bytes",
    "evidence_ref",
})
QA_PREFLIGHT_KEYS = frozenset({"environment", "evidence_ref"})
CONTROL_KEYS = frozenset({"status", "owner", "verified_on", "evidence_ref"})
AT_REST_DECISION_KEYS = frozenset({
    "disposition", "owner", "decided_on", "evidence_ref",
})
APPROVAL_KEYS = frozenset({
    "status", "approver", "approved_on", "evidence_ref",
})
PLACEHOLDER_TOKENS = (
    "placeholder", "n/a", "unavailable", "waived", "todo", "tbd",
    "unknown", "none", "unassigned", "sample", "example", "fake", "dummy",
)


def _error(pointer, reason):
    raise CommandError(f"{pointer}: {reason}")


def _exact_object(value, expected, pointer):
    if type(value) is not dict:
        _error(pointer, "must be an object")
    missing = sorted(expected - set(value))
    if missing:
        child = f"{pointer}/{missing[0]}" if pointer else f"/{missing[0]}"
        _error(child, "required key is missing")
    extra = sorted(set(value) - expected)
    if extra:
        child = f"{pointer}/{extra[0]}" if pointer else f"/{extra[0]}"
        _error(child, "unexpected key")


def _date(value, pointer, *, nullable=False):
    if nullable and value is None:
        return
    if (
        type(value) is not str
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None
    ):
        _error(pointer, "date must be a real YYYY-MM-DD value not in the future")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _error(pointer, "date must be a real YYYY-MM-DD value not in the future")
    if parsed > date.today():
        _error(pointer, "date must be a real YYYY-MM-DD value not in the future")


def _text(value, pointer, *, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or not value.strip():
        _error(pointer, "non-empty text is required")
    _reject_placeholder(value, pointer)


def _reject_placeholder(value, pointer):
    lowered = value.casefold()
    if any(
        re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered)
        for token in PLACEHOLDER_TOKENS
    ):
        _error(pointer, "placeholder token is not allowed")


def _reference(value, pointer, *, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or not value.strip():
        _error(pointer, "reference must be a safe repository path or HTTPS URL")
    parsed = urlsplit(value)
    if parsed.scheme:
        safe = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
        if not safe:
            _error(pointer, "reference must be a safe repository path or HTTPS URL")
    else:
        path = PurePosixPath(value)
        safe = (
            not path.is_absolute()
            and ".." not in path.parts
            and value.startswith("docs/")
            and "\\" not in value
            and not parsed.query
            and not parsed.fragment
            and path.as_posix() == value
        )
        candidate = Path(settings.BASE_DIR, *path.parts)
        if not safe or not candidate.is_file():
            _error(
                pointer,
                "local reference must be a normalized existing docs file",
            )
    _reject_placeholder(value, pointer)


def _nonnegative_integer(value, pointer):
    if type(value) is not int or value < 0:
        _error(pointer, "must be a non-negative integer")


def validate_manifest(manifest):
    _exact_object(manifest, TOP_LEVEL_KEYS, "")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
    ):
        _error("/schema_version", "schema version is invalid")
    if manifest["status"] not in {"blocked", "approved"}:
        _error("/status", "status is invalid")
    _date(manifest["reviewed_on"], "/reviewed_on")

    preflight = manifest["candidate_preflight"]
    _exact_object(preflight, PREFLIGHT_KEYS, "/candidate_preflight")
    if preflight["status"] not in {"blocked", "passed", "failed"}:
        _error("/candidate_preflight/status", "status is invalid")
    eligible_fields = PREFLIGHT_KEYS - {"status"}
    if preflight["status"] == "blocked":
        non_null = sorted(name for name in eligible_fields if preflight[name] is not None)
        if non_null:
            _error(
                f"/candidate_preflight/{non_null[0]}",
                "blocked candidate fields must be null",
            )
    else:
        if preflight["provenance"] != "approved-production-clone":
            _error(
                "/candidate_preflight/provenance",
                "approval requires an approved-production-clone run",
            )
        if preflight["environment"] != "production":
            _error(
                "/candidate_preflight/environment",
                "candidate environment must be production",
            )
        _date(preflight["checked_on"], "/candidate_preflight/checked_on")
        for name in (
            "checked", "supported", "unsupported", "total_bytes", "max_bytes",
            "limit_bytes",
        ):
            _nonnegative_integer(preflight[name], f"/candidate_preflight/{name}")
        _reference(preflight["evidence_ref"], "/candidate_preflight/evidence_ref")
    if preflight["status"] != "blocked" and (
        preflight["supported"] + preflight["unsupported"]
        != preflight["checked"]
    ):
        _error(
            "/candidate_preflight/supported",
            "supported plus unsupported must equal checked",
        )
    if preflight["status"] == "passed" and preflight["unsupported"]:
        _error(
            "/candidate_preflight/status",
            "passed preflight cannot contain unsupported children",
        )
    if (
        preflight["status"] == "passed"
        and preflight["max_bytes"] > preflight["limit_bytes"]
    ):
        _error(
            "/candidate_preflight/max_bytes",
            "passed preflight cannot exceed limit_bytes",
        )
    if (
        preflight["status"] != "blocked"
        and preflight["max_bytes"] > preflight["total_bytes"]
    ):
        _error("/candidate_preflight/max_bytes", "cannot exceed total_bytes")

    qa_preflight = manifest["qa_preflight"]
    _exact_object(qa_preflight, QA_PREFLIGHT_KEYS, "/qa_preflight")
    if qa_preflight["environment"] != "development-qa":
        _error("/qa_preflight/environment", "environment is invalid")
    _reference(qa_preflight["evidence_ref"], "/qa_preflight/evidence_ref")

    controls = manifest["controls"]
    _exact_object(controls, CONTROL_NAMES, "/controls")
    blocked_controls = set()
    for name in sorted(CONTROL_NAMES):
        control = controls[name]
        pointer = f"/controls/{name}"
        _exact_object(control, CONTROL_KEYS, pointer)
        if control["status"] not in {"blocked", "verified"}:
            _error(f"{pointer}/status", "status is invalid")
        _text(control["owner"], f"{pointer}/owner")
        _date(control["verified_on"], f"{pointer}/verified_on", nullable=True)
        _reference(control["evidence_ref"], f"{pointer}/evidence_ref")
        if control["status"] == "verified" and control["verified_on"] is None:
            _error(f"{pointer}/verified_on", "verified date is required")
        if control["status"] == "blocked":
            blocked_controls.add(name)

    blockers = manifest["blockers"]
    if type(blockers) is not list or any(
        type(name) is not str or name not in CONTROL_NAMES for name in blockers
    ) or len(blockers) != len(set(blockers)):
        _error("/blockers", "must contain unique control names")
    if set(blockers) != blocked_controls:
        _error("/blockers", "must exactly match blocked controls")

    at_rest = manifest["at_rest_decision"]
    _exact_object(at_rest, AT_REST_DECISION_KEYS, "/at_rest_decision")
    if at_rest["disposition"] not in {
        "pending", "reopen-required", "accepted", "reopened",
    }:
        _error("/at_rest_decision/disposition", "disposition is invalid")
    if preflight["status"] == "failed" and at_rest["disposition"] != "reopened":
        _error(
            "/at_rest_decision/disposition",
            "failed candidate requires a recorded reopened decision",
        )
    if manifest["status"] == "approved" and at_rest["disposition"] != "accepted":
        _error(
            "/at_rest_decision/disposition",
            "approved readiness requires an accepted at-rest decision",
        )
    if at_rest["disposition"] in {"accepted", "reopened"}:
        if at_rest["owner"] is None:
            _error("/at_rest_decision/owner", "named owner is required")
        _text(at_rest["owner"], "/at_rest_decision/owner")
        if at_rest["decided_on"] is None:
            _error("/at_rest_decision/decided_on", "decision date is required")
        _date(at_rest["decided_on"], "/at_rest_decision/decided_on")
        if at_rest["evidence_ref"] is None:
            _error(
                "/at_rest_decision/evidence_ref",
                "decision evidence reference is required",
            )
        _reference(at_rest["evidence_ref"], "/at_rest_decision/evidence_ref")
    elif any(at_rest[name] is not None for name in (
        "owner", "decided_on", "evidence_ref",
    )):
        _error(
            "/at_rest_decision/disposition",
            "pending decision fields must be null",
        )

    approval = manifest["approval"]
    _exact_object(approval, APPROVAL_KEYS, "/approval")
    if approval["status"] not in {"blocked", "approved"}:
        _error("/approval/status", "status is invalid")
    if approval["status"] == "approved" and blockers:
        _error("/approval/status", "approval cannot coexist with blockers")
    if approval["status"] == "approved":
        if approval["approver"] is None:
            _error("/approval/approver", "named approver is required")
        _text(approval["approver"], "/approval/approver")
        _date(approval["approved_on"], "/approval/approved_on")
        if approval["evidence_ref"] is None:
            _error(
                "/approval/evidence_ref",
                "approval evidence reference is required",
            )
        _reference(approval["evidence_ref"], "/approval/evidence_ref")
    else:
        if any(approval[name] is not None for name in (
            "approver", "approved_on", "evidence_ref",
        )):
            _error("/approval/status", "blocked approval fields must be null")

    if manifest["status"] == "approved" and (
        blockers
        or approval["status"] != "approved"
        or preflight["status"] != "passed"
    ):
        _error("/status", "approved readiness is inconsistent")
    if manifest["status"] == "blocked" and approval["status"] != "blocked":
        _error("/status", "blocked readiness is inconsistent")
    return manifest


class Command(BaseCommand):
    help = "Lint the audit-security readiness manifest without echoing values."

    def add_arguments(self, parser):
        parser.add_argument("--manifest")
        parser.add_argument("--require-approved", action="store_true")

    def handle(self, *args, **options):
        manifest_path = options.get("manifest")
        path = (
            Path(manifest_path)
            if manifest_path
            else Path(settings.BASE_DIR)
            / "docs/operations/audit-security-readiness.json"
        )
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            _error("/", "manifest could not be read as JSON")
        validate_manifest(manifest)
        if options.get("require_approved") and manifest["status"] != "approved":
            _error("/status", "approved readiness is required")
        self.stdout.write(f"audit_security_readiness status={manifest['status']}")
