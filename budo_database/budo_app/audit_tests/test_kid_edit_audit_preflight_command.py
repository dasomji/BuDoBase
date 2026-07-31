"""RED contract for the non-sensitive kid-edit audit preflight (#164-03)."""

from copy import deepcopy
from datetime import date
import importlib
from io import StringIO
import re
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import QuerySet
from django.test import TestCase

from budo_app.audit_tests.test_kid_edit_audit_schema import valid_details
from budo_app.models import Kinder, Turnus


COMMAND_MODULE = (
    "budo_app.management.commands.check_kid_edit_audit_payloads"
)
try:
    command_module = importlib.import_module(COMMAND_MODULE)
except ModuleNotFoundError as error:
    if error.name != COMMAND_MODULE:
        raise
    command_module = None


class KidEditAuditPreflightCommandTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=164, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=165, turnus_beginn=date(2026, 8, 1),
        )

    def require_command(self):
        self.assertIsNotNone(
            command_module,
            "check_kid_edit_audit_payloads is not implemented yet",
        )

    def child(self, turnus, *, marker, illness=None):
        return Kinder.objects.create(
            kid_index=f"index-{marker}", turnus=turnus,
            kid_vorname=f"SECRET-FIRST-{marker}",
            kid_nachname=f"SECRET-LAST-{marker}",
            anmelder_vorname="", anmelder_nachname="",
            rechnungsadresse="", rechnung_ort="", rechnung_land="",
            illness=illness,
        )

    def run_command(self, *args):
        self.require_command()
        stdout = StringIO()
        stderr = StringIO()
        call_command(
            "check_kid_edit_audit_payloads", *args,
            stdout=stdout, stderr=stderr, no_color=True,
        )
        return stdout.getvalue() + stderr.getvalue()

    def assert_private_output(self, output, *secrets):
        for secret in secrets:
            self.assertNotIn(secret, output)
        self.assertNotIn("kid_vorname", output)
        self.assertNotIn("kid_nachname", output)
        self.assertNotIn("illness=", output)

    def test_candidate_turnus_or_all_children_use_explicit_loaded_snapshot_inputs(self):
        selected = self.child(self.turnus, marker="SELECTED")
        other = self.child(self.other_turnus, marker="OTHER")
        self.require_command()
        with mock.patch.object(
            command_module,
            "serialize_kid_edit_snapshot",
            wraps=command_module.serialize_kid_edit_snapshot,
        ) as serializer:
            candidate_output = self.run_command("--turnus-id", str(self.turnus.pk))

        self.assertIn("checked=1", candidate_output)
        self.assertIn("unsupported=0", candidate_output)
        self.assertRegex(candidate_output, r"total_bytes=\d+")
        self.assertRegex(candidate_output, r"max_bytes=\d+")
        self.assertIn("limit_bytes=4194304", candidate_output)
        self.assertEqual(serializer.call_count, 1)
        kwargs = serializer.call_args.kwargs
        self.assertEqual(kwargs["child"].pk, selected.pk)
        self.assertFalse(kwargs["child"].get_deferred_fields())
        for name in (
            "active_periods", "focus_links", "active_events", "assignments",
        ):
            self.assertNotIsInstance(kwargs[name], QuerySet)
            self.assertIsInstance(kwargs[name], (list, tuple))
        self.assert_private_output(
            candidate_output, "SECRET-FIRST-SELECTED", "SECRET-LAST-SELECTED",
            "SECRET-FIRST-OTHER", "SECRET-LAST-OTHER",
        )

        all_output = self.run_command()
        self.assertIn("checked=2", all_output)
        self.assertIn("unsupported=0", all_output)
        self.assert_private_output(all_output, "SECRET-FIRST", "SECRET-LAST")
        self.assertTrue(Kinder.objects.filter(pk=other.pk).exists())

    def test_zero_child_candidate_is_successful_and_has_zero_safe_aggregates(self):
        output = self.run_command("--turnus-id", str(self.turnus.pk))
        self.assertIn("checked=0", output)
        self.assertIn("supported=0", output)
        self.assertIn("unsupported=0", output)
        self.assertIn("total_bytes=0", output)
        self.assertIn("max_bytes=0", output)
        self.assertIn("limit_bytes=4194304", output)

    def test_nonexistent_zero_and_negative_candidate_ids_fail_with_fixed_safe_error(self):
        nonexistent = max(self.turnus.pk, self.other_turnus.pk) + 10_000
        for turnus_id in (nonexistent, 0, -1):
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(turnus_id=turnus_id):
                with self.assertRaises(CommandError) as raised:
                    call_command(
                        "check_kid_edit_audit_payloads",
                        "--turnus-id", str(turnus_id),
                        stdout=stdout, stderr=stderr, no_color=True,
                    )
                self.assertEqual(
                    str(raised.exception),
                    "Candidate Turnus is unavailable.",
                )
                output = stdout.getvalue() + stderr.getvalue()
                self.assertNotIn(str(turnus_id), output)
                self.assertNotIn("checked=0", output)

    def assert_safe_unsupported_line(
        self, output, *, path, marker, forbidden=(),
    ):
        matching = [
            line for line in output.splitlines()
            if f"path={path}" in line
        ]
        self.assertEqual(len(matching), 1)
        self.assertRegex(
            matching[0],
            rf"^child_ordinal=1 path={re.escape(path)} bytes=\d+$",
        )
        self.assertNotIn("child_id=", output)
        self.assertNotIn("turnus_id=", output)
        self.assertNotIn(f"index-{marker}", output)
        for value in forbidden:
            self.assertNotIn(str(value), output)

    def test_per_string_and_unsupported_type_fail_with_only_ordinal_path_and_bytes(self):
        self.child(
            self.turnus,
            marker="UNSUPPORTED",
            illness="SECRET-ILLNESS-" + "x" * 10_001,
        )
        stdout = StringIO()
        stderr = StringIO()
        self.require_command()
        with self.assertRaises(CommandError):
            call_command(
                "check_kid_edit_audit_payloads",
                "--turnus-id", str(self.turnus.pk),
                stdout=stdout, stderr=stderr, no_color=True,
            )
        output = stdout.getvalue() + stderr.getvalue()
        self.assert_safe_unsupported_line(
            output, path="fields.illness", marker="UNSUPPORTED",
        )
        self.assertIn("unsupported=1", output)
        self.assert_private_output(output, "SECRET-ILLNESS", "SECRET-FIRST")

        invalid_snapshot = valid_details()["before"]
        invalid_snapshot["fields"]["stay_weeks"] = 1.5
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch.object(
            command_module,
            "serialize_kid_edit_snapshot",
            return_value=invalid_snapshot,
        ), self.assertRaises(CommandError):
            call_command(
                "check_kid_edit_audit_payloads",
                "--turnus-id", str(self.turnus.pk),
                stdout=stdout, stderr=stderr, no_color=True,
            )
        output = stdout.getvalue() + stderr.getvalue()
        self.assert_safe_unsupported_line(
            output, path="fields.stay_weeks", marker="UNSUPPORTED",
        )
        self.assertIn("unsupported=1", output)
        self.assertNotIn("1.5", output)

        invalid_snapshot = valid_details()["before"]
        leaked_period_id = 876_543_210
        invalid_snapshot["swp"][0]["period_id"] = leaked_period_id
        invalid_snapshot["swp"][0]["duration_days"] = 0
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch.object(
            command_module,
            "serialize_kid_edit_snapshot",
            return_value=invalid_snapshot,
        ), self.assertRaises(CommandError):
            call_command(
                "check_kid_edit_audit_payloads",
                "--turnus-id", str(self.turnus.pk),
                stdout=stdout, stderr=stderr, no_color=True,
            )
        output = stdout.getvalue() + stderr.getvalue()
        self.assert_safe_unsupported_line(
            output,
            path="swp.0",
            marker="UNSUPPORTED",
            forbidden=(leaked_period_id,),
        )

    def test_missing_nullable_and_unknown_fields_report_deterministic_safe_paths(self):
        self.child(self.turnus, marker="STRUCTURE")
        missing = deepcopy(valid_details()["before"])
        missing["fields"].pop("siblings")
        unknown = deepcopy(valid_details()["before"])
        unknown["fields"]["unexpected_field"] = "SECRET-UNKNOWN-VALUE"
        for snapshot, expected_path in (
            (missing, "fields.siblings"),
            (unknown, "fields.unexpected_field"),
        ):
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(path=expected_path):
                with mock.patch.object(
                    command_module,
                    "serialize_kid_edit_snapshot",
                    return_value=snapshot,
                ), self.assertRaises(CommandError):
                    call_command(
                        "check_kid_edit_audit_payloads",
                        "--turnus-id", str(self.turnus.pk),
                        stdout=stdout, stderr=stderr, no_color=True,
                    )
                output = stdout.getvalue() + stderr.getvalue()
                self.assert_safe_unsupported_line(
                    output, path=expected_path, marker="STRUCTURE",
                )
                self.assertIn("unsupported=1", output)
                self.assertNotIn("SECRET-UNKNOWN-VALUE", output)
                self.assertNotIn("SECRET-FIRST-STRUCTURE", output)

    def test_over_four_mib_fails_with_size_root_path_and_no_payload_values(self):
        self.child(self.turnus, marker="OVERSIZE")
        oversized = deepcopy(valid_details()["before"])
        oversized["swp"][0]["focuses"] = [
            {
                "id": 1_000 + index,
                "label": f"z{index:08d}" + "X" * (255 - 9),
            }
            for index in range(16_000)
        ]
        self.require_command()
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch.object(
            command_module,
            "serialize_kid_edit_snapshot",
            return_value=oversized,
        ), self.assertRaises(CommandError):
            call_command(
                "check_kid_edit_audit_payloads",
                "--turnus-id", str(self.turnus.pk),
                stdout=stdout, stderr=stderr, no_color=True,
            )
        output = stdout.getvalue() + stderr.getvalue()
        self.assert_safe_unsupported_line(
            output, path="$", marker="OVERSIZE",
        )
        self.assertRegex(output, r"child_ordinal=1 path=\$ bytes=[4-9][0-9]{6,}")
        self.assertIn("limit_bytes=4194304", output)
        self.assertIn("unsupported=1", output)
        self.assert_private_output(output, "SECRET-FIRST-OVERSIZE", "XXXXX")
