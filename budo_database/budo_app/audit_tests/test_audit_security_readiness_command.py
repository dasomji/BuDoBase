"""RED contract for repository-safe audit-security readiness linting (#165-01)."""

from copy import deepcopy
from datetime import date
import importlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


COMMAND_MODULE = "budo_app.management.commands.check_audit_security_readiness"
try:
    command_module = importlib.import_module(COMMAND_MODULE)
except ModuleNotFoundError as error:
    if error.name != COMMAND_MODULE:
        raise
    command_module = None

CONTROL_NAMES = (
    "storage_encryption",
    "database_transport",
    "browser_transport",
    "credentials_and_mfa",
    "logging_exclusions",
    "backup_and_export_handling",
    "permission_assignments",
    "restore_and_deletion_reconciliation",
    "incident_response",
)
TOP_LEVEL_KEYS = {
    "schema_version",
    "status",
    "reviewed_on",
    "candidate_preflight",
    "qa_preflight",
    "controls",
    "blockers",
    "at_rest_decision",
    "approval",
}
PREFLIGHT_KEYS = {
    "status",
    "environment",
    "provenance",
    "checked_on",
    "checked",
    "supported",
    "unsupported",
    "total_bytes",
    "max_bytes",
    "limit_bytes",
    "evidence_ref",
}
QA_PREFLIGHT_KEYS = {"environment", "evidence_ref"}
CONTROL_KEYS = {"status", "owner", "verified_on", "evidence_ref"}
AT_REST_DECISION_KEYS = {
    "disposition", "owner", "decided_on", "evidence_ref",
}
APPROVAL_KEYS = {"status", "approver", "approved_on", "evidence_ref"}


def blocked_manifest():
    checked_on = date.today().isoformat()
    controls = {
        name: {
            "status": "verified",
            "owner": "Operations Security",
            "verified_on": checked_on,
            "evidence_ref": "docs/operations/audit-security-readiness.md",
        }
        for name in CONTROL_NAMES
    }
    controls["restore_and_deletion_reconciliation"]["status"] = "blocked"
    return {
        "schema_version": 1,
        "status": "blocked",
        "reviewed_on": checked_on,
        "candidate_preflight": {
            "status": "blocked",
            "environment": None,
            "provenance": None,
            "checked_on": None,
            "checked": None,
            "supported": None,
            "unsupported": None,
            "total_bytes": None,
            "max_bytes": None,
            "limit_bytes": None,
            "evidence_ref": None,
        },
        "qa_preflight": {
            "environment": "development-qa",
            "evidence_ref": "docs/evidence/165/dev-qa-preflight.md",
        },
        "controls": controls,
        "blockers": ["restore_and_deletion_reconciliation"],
        "at_rest_decision": {
            "disposition": "pending",
            "owner": None,
            "decided_on": None,
            "evidence_ref": None,
        },
        "approval": {
            "status": "blocked",
            "approver": None,
            "approved_on": None,
            "evidence_ref": None,
        },
    }


def approved_manifest():
    manifest = blocked_manifest()
    manifest["status"] = "approved"
    manifest["candidate_preflight"] = {
        "status": "passed",
        "environment": "production",
        "provenance": "approved-production-clone",
        "checked_on": date.today().isoformat(),
        "checked": 12,
        "supported": 12,
        "unsupported": 0,
        "total_bytes": 24000,
        "max_bytes": 2100,
        "limit_bytes": 4194304,
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    manifest["controls"]["restore_and_deletion_reconciliation"][
        "status"
    ] = "verified"
    manifest["controls"]["storage_encryption"]["evidence_ref"] = (
        "https://security.vendor.test/audit-security/storage"
    )
    manifest["blockers"] = []
    manifest["at_rest_decision"] = {
        "disposition": "accepted",
        "owner": "Production Data Owner",
        "decided_on": date.today().isoformat(),
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    manifest["approval"] = {
        "status": "approved",
        "approver": "Production Security Owner",
        "approved_on": date.today().isoformat(),
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    return manifest


def failed_candidate_manifest():
    manifest = blocked_manifest()
    manifest["candidate_preflight"] = {
        "status": "failed",
        "environment": "production",
        "provenance": "approved-production-clone",
        "checked_on": date.today().isoformat(),
        "checked": 12,
        "supported": 11,
        "unsupported": 1,
        "total_bytes": 24000,
        "max_bytes": 2100,
        "limit_bytes": 4194304,
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    manifest["at_rest_decision"] = {
        "disposition": "reopened",
        "owner": "Production Data Owner",
        "decided_on": date.today().isoformat(),
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    return manifest


class AuditSecurityReadinessCommandTests(SimpleTestCase):
    def require_command(self):
        self.assertIsNotNone(
            command_module,
            "check_audit_security_readiness is not implemented yet",
        )

    def invoke(self, manifest, *options):
        self.require_command()
        with TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "readiness.json"
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            try:
                call_command(
                    "check_audit_security_readiness",
                    "--manifest",
                    str(manifest_path),
                    *options,
                    stdout=stdout,
                    stderr=stderr,
                    no_color=True,
                )
            except CommandError as error:
                self.fail(f"valid manifest was rejected: {error}")
            return stdout.getvalue() + stderr.getvalue()

    def assert_rejected(self, manifest, pointer, reason, secret=None, *options):
        self.require_command()
        with TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "readiness.json"
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            with self.assertRaises(CommandError) as raised:
                call_command(
                    "check_audit_security_readiness",
                    "--manifest",
                    str(manifest_path),
                    *options,
                    stdout=stdout,
                    stderr=stderr,
                    no_color=True,
                )
        expected = f"{pointer}: {reason}"
        self.assertEqual(str(raised.exception), expected)
        rendered = str(raised.exception) + stdout.getvalue() + stderr.getvalue()
        if secret is not None:
            self.assertNotIn(secret, rendered)

    def test_exact_schema_accepts_honest_blocked_lint_but_approval_gate_rejects_it(self):
        manifest = blocked_manifest()
        self.assertEqual(set(manifest), TOP_LEVEL_KEYS)
        self.assertEqual(set(manifest["candidate_preflight"]), PREFLIGHT_KEYS)
        self.assertEqual(set(manifest["qa_preflight"]), QA_PREFLIGHT_KEYS)
        self.assertEqual(set(manifest["controls"]), set(CONTROL_NAMES))
        for control in manifest["controls"].values():
            self.assertEqual(set(control), CONTROL_KEYS)
        self.assertEqual(set(manifest["approval"]), APPROVAL_KEYS)
        self.assertEqual(
            set(manifest["at_rest_decision"]), AT_REST_DECISION_KEYS,
        )

        output = self.invoke(manifest)
        self.assertIn("status=blocked", output)
        self.assertNotIn("restore_and_deletion_reconciliation", output)
        self.assert_rejected(
            manifest,
            "/status",
            "approved readiness is required",
            None,
            "--require-approved",
        )

    def test_synthetic_fully_approved_manifest_passes_the_approval_gate(self):
        output = self.invoke(approved_manifest(), "--require-approved")
        self.assertIn("status=approved", output)
        self.assertNotIn("Production Security Owner", output)
        self.assertNotIn("security.vendor.test", output)

    def test_candidate_gate_requires_approved_production_clone_not_qa_aggregates(self):
        blocked = blocked_manifest()
        self.assertTrue(all(
            blocked["candidate_preflight"][name] is None
            for name in PREFLIGHT_KEYS - {"status"}
        ))
        self.assertEqual(
            blocked["qa_preflight"],
            {
                "environment": "development-qa",
                "evidence_ref": "docs/evidence/165/dev-qa-preflight.md",
            },
        )
        self.invoke(blocked)

        qa_as_candidate = approved_manifest()
        qa_as_candidate["candidate_preflight"]["environment"] = (
            "development-qa"
        )
        qa_as_candidate["candidate_preflight"]["provenance"] = (
            "development-qa"
        )
        self.assert_rejected(
            qa_as_candidate,
            "/candidate_preflight/provenance",
            "approval requires an approved-production-clone run",
            "development-qa",
            "--require-approved",
        )

    def test_at_rest_decision_tracks_pending_acceptance_and_reopening(self):
        reopen_required = blocked_manifest()
        reopen_required["at_rest_decision"]["disposition"] = (
            "reopen-required"
        )
        self.invoke(reopen_required)
        self.invoke(failed_candidate_manifest())

        invalid = approved_manifest()
        invalid["at_rest_decision"] = {
            "disposition": "pending",
            "owner": None,
            "decided_on": None,
            "evidence_ref": None,
        }
        self.assert_rejected(
            invalid,
            "/at_rest_decision/disposition",
            "approved readiness requires an accepted at-rest decision",
        )

        invalid = failed_candidate_manifest()
        invalid["at_rest_decision"]["disposition"] = "pending"
        invalid["at_rest_decision"]["owner"] = None
        invalid["at_rest_decision"]["decided_on"] = None
        invalid["at_rest_decision"]["evidence_ref"] = None
        self.assert_rejected(
            invalid,
            "/at_rest_decision/disposition",
            "failed candidate requires a recorded reopened decision",
        )

        for field, pointer, reason in (
            ("owner", "/at_rest_decision/owner", "named owner is required"),
            (
                "decided_on",
                "/at_rest_decision/decided_on",
                "decision date is required",
            ),
            (
                "evidence_ref",
                "/at_rest_decision/evidence_ref",
                "decision evidence reference is required",
            ),
        ):
            invalid = approved_manifest()
            invalid["at_rest_decision"][field] = None
            with self.subTest(field=field):
                self.assert_rejected(invalid, pointer, reason)

    def test_missing_extra_and_placeholder_values_are_rejected_without_echoing_values(self):
        self.require_command()
        self.invoke(blocked_manifest())
        missing_top = blocked_manifest()
        missing_top.pop("reviewed_on")
        extra_preflight = blocked_manifest()
        extra_preflight["candidate_preflight"]["notes"] = "SECRET-NOTES"
        missing_control = blocked_manifest()
        missing_control["controls"]["storage_encryption"].pop("owner")
        extra_approval = blocked_manifest()
        extra_approval["approval"]["ticket"] = "SECRET-TICKET"
        cases = (
            (
                missing_top,
                "/reviewed_on",
                "required key is missing",
                None,
            ),
            (
                extra_preflight,
                "/candidate_preflight/notes",
                "unexpected key",
                "SECRET-NOTES",
            ),
            (
                missing_control,
                "/controls/storage_encryption/owner",
                "required key is missing",
                None,
            ),
            (
                extra_approval,
                "/approval/ticket",
                "unexpected key",
                "SECRET-TICKET",
            ),
        )
        for manifest, pointer, reason, secret in cases:
            with self.subTest(pointer=pointer):
                self.assert_rejected(manifest, pointer, reason, secret)

        for token in (
            "placeholder", "N/A", "unavailable", "waived", "TODO", "TBD",
            "unknown", "none", "unassigned", "sample", "example", "fake",
            "dummy",
        ):
            manifest = blocked_manifest()
            secret = f"{token}-SECRET-VALUE"
            manifest["controls"]["storage_encryption"]["owner"] = secret
            with self.subTest(token=token):
                self.assert_rejected(
                    manifest,
                    "/controls/storage_encryption/owner",
                    "placeholder token is not allowed",
                    secret,
                )

    def test_unsafe_evidence_references_and_invalid_or_future_dates_are_rejected(self):
        self.require_command()
        self.invoke(blocked_manifest())
        for unsafe_ref in (
            "https://user:password@evidence.example.org/report",
            "https://evidence.example.org/report?token=SECRET-QUERY",
            "http://evidence.example.org/report",
        ):
            manifest = blocked_manifest()
            manifest["controls"]["storage_encryption"][
                "evidence_ref"
            ] = unsafe_ref
            with self.subTest(reference=unsafe_ref):
                self.assert_rejected(
                    manifest,
                    "/controls/storage_encryption/evidence_ref",
                    "reference must be a safe repository path or HTTPS URL",
                    unsafe_ref,
                )

        for unsafe_local_ref in (
            "docs/operations/../operations/audit-security-readiness.md",
            "docs/operations",
            "docs/operations/missing-readiness-evidence.md",
        ):
            manifest = blocked_manifest()
            manifest["controls"]["storage_encryption"][
                "evidence_ref"
            ] = unsafe_local_ref
            with self.subTest(reference=unsafe_local_ref):
                self.assert_rejected(
                    manifest,
                    "/controls/storage_encryption/evidence_ref",
                    "local reference must be a normalized existing docs file",
                    unsafe_local_ref,
                )

        for invalid_date in ("2026-02-30", "9999-01-01"):
            manifest = blocked_manifest()
            manifest["reviewed_on"] = invalid_date
            with self.subTest(date=invalid_date):
                self.assert_rejected(
                    manifest,
                    "/reviewed_on",
                    "date must be a real YYYY-MM-DD value not in the future",
                    invalid_date,
                )

    def test_evidence_references_reject_expanded_placeholders_without_echoing_them(self):
        self.require_command()
        self.invoke(blocked_manifest())
        for token in (
            "TODO", "TBD", "unknown", "none", "unassigned", "sample",
            "example", "fake", "dummy",
        ):
            manifest = blocked_manifest()
            secret = f"{token}-SECRET-REFERENCE"
            manifest["controls"]["storage_encryption"]["evidence_ref"] = (
                f"https://security.vendor.test/evidence/{secret}"
            )
            self.assert_rejected(
                manifest,
                "/controls/storage_encryption/evidence_ref",
                "placeholder token is not allowed",
                secret,
            )

    def test_status_count_size_unsupported_and_approval_relations_are_enforced(self):
        self.require_command()
        self.invoke(blocked_manifest())
        cases = []

        manifest = approved_manifest()
        manifest["candidate_preflight"]["status"] = "skipped"
        cases.append((
            manifest,
            "/candidate_preflight/status",
            "status is invalid",
            "skipped",
        ))

        manifest = approved_manifest()
        manifest["candidate_preflight"]["checked"] = -1
        cases.append((
            manifest,
            "/candidate_preflight/checked",
            "must be a non-negative integer",
            None,
        ))

        manifest = approved_manifest()
        manifest["candidate_preflight"]["supported"] = 11
        cases.append((
            manifest,
            "/candidate_preflight/supported",
            "supported plus unsupported must equal checked",
            None,
        ))

        manifest = approved_manifest()
        manifest["candidate_preflight"]["unsupported"] = 1
        manifest["candidate_preflight"]["supported"] = 11
        cases.append((
            manifest,
            "/candidate_preflight/status",
            "passed preflight cannot contain unsupported children",
            None,
        ))

        manifest = approved_manifest()
        manifest["candidate_preflight"]["max_bytes"] = 4194305
        manifest["candidate_preflight"]["total_bytes"] = 4194305
        cases.append((
            manifest,
            "/candidate_preflight/max_bytes",
            "passed preflight cannot exceed limit_bytes",
            None,
        ))

        manifest = blocked_manifest()
        manifest["approval"] = {
            "status": "approved",
            "approver": "Production Security Owner",
            "approved_on": date.today().isoformat(),
            "evidence_ref": "docs/operations/audit-security/sign-off.md",
        }
        cases.append((
            manifest,
            "/approval/status",
            "approval cannot coexist with blockers",
            None,
        ))

        for field, pointer, reason in (
            ("approver", "/approval/approver", "named approver is required"),
            (
                "evidence_ref",
                "/approval/evidence_ref",
                "approval evidence reference is required",
            ),
        ):
            manifest = approved_manifest()
            manifest["approval"][field] = None
            cases.append((manifest, pointer, reason, None))

        for manifest, pointer, reason, secret in cases:
            with self.subTest(pointer=pointer, reason=reason):
                self.assert_rejected(manifest, pointer, reason, secret)
