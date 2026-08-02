"""RED contracts for kid-edit snapshot serialization and command HMAC (#164-02)."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date
import re
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings

from budo_app.kid_edit_contracts import FIELD_CONTRACTS
from budo_app.kid_edit_contracts.decoder import HappyCleaningTarget, SwpTarget
from budo_app.kid_edit_contracts.validation import (
    ValidatedKidEditCommand,
    ValidatedKidEditHappyCleaning,
    ValidatedKidEditSwp,
)
from budo_app.models import Kinder, Turnus

try:
    import budo_app.kid_edit_audit_snapshot as snapshot_module
    from budo_app.kid_edit_audit_snapshot import (
        LoadedKidEditAssignment,
        LoadedKidEditEvent,
        LoadedKidEditFocusLink,
        LoadedKidEditPeriod,
        build_kid_edit_audit_details,
        serialize_kid_edit_snapshot,
    )
except ModuleNotFoundError as error:
    if error.name != "budo_app.kid_edit_audit_snapshot":
        raise
    snapshot_module = None
    LoadedKidEditAssignment = None
    LoadedKidEditEvent = None
    LoadedKidEditFocusLink = None
    LoadedKidEditPeriod = None
    build_kid_edit_audit_details = None
    serialize_kid_edit_snapshot = None

try:
    import budo_app.kid_edit_fingerprint as fingerprint_module
    from budo_app.kid_edit_fingerprint import (
        KID_EDIT_FINGERPRINT_SALT,
        sign_kid_edit_command,
        verify_kid_edit_command_fingerprint,
    )
except ModuleNotFoundError as error:
    if error.name != "budo_app.kid_edit_fingerprint":
        raise
    fingerprint_module = None
    KID_EDIT_FINGERPRINT_SALT = None
    sign_kid_edit_command = None
    verify_kid_edit_command_fingerprint = None


FINGERPRINT_PATTERN = re.compile(r"\Ahmac-sha256:v1:[0-9a-f]{64}\Z")
FINGERPRINT_SALT = "budo.kid-edit.command-fingerprint.v1"


RAW_FIELDS = {
    "first_name": "  Ada  ", "last_name": "", "sex": " - ",
    "birthday": "2012-02-29", "stay_weeks": 7, "siblings": None,
    "tent_request": " Bea\nGrace ", "budo_experience": False,
    "social_security_number": " 0202 121234 ", "illness": " NEIN ",
    "drugs": "", "vegetarian": "Legacy-Veg", "special_food": None,
    "swimmer": "  mittel  ", "consent": None,
    "over_the_counter_medication": "Bei Bedarf\n  ",
    "prescription_medication": None, "tetanus": " - ",
    "tick_vaccine": "Nein", "organization": "", "registrant_first_name": " ",
    "registrant_last_name": "Lovelace", "registrant_email": " ADA@EXAMPLE.ORG ",
    "registrant_phone": "+43  660", "insured_with": None,
    "emergency_contacts": "Charles\n+43", "budo_family": "legacy-family",
}


def assert_plain_json(testcase, value):
    testcase.assertIn(type(value), {dict, list, str, int, bool, type(None)})
    if type(value) is dict:
        for key, item in value.items():
            testcase.assertIs(type(key), str)
            assert_plain_json(testcase, item)
    elif type(value) is list:
        for item in value:
            assert_plain_json(testcase, item)


class KidEditSnapshotSerializationTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        storage = {
            field.storage_name: (
                date.fromisoformat(RAW_FIELDS[field.api_name])
                if field.api_name == "birthday" else RAW_FIELDS[field.api_name]
            )
            for field in FIELD_CONTRACTS
        }
        self.child = Kinder.objects.create(
            kid_index="kid-164", turnus=self.turnus,
            rechnungsadresse="", rechnung_ort="", rechnung_land="",
            edit_version=4, happy_cleaning_number=42,
            happy_cleaning_number_version=3, **storage,
        )
        self.child = Kinder.objects.get(pk=self.child.pk)

    def loaded(self):
        for seam in (
            LoadedKidEditPeriod, LoadedKidEditFocusLink, LoadedKidEditEvent,
            LoadedKidEditAssignment, serialize_kid_edit_snapshot,
        ):
            self.assertTrue(callable(seam), "snapshot serializer is not implemented")
        periods = (
            LoadedKidEditPeriod(18, "w2", "Woche 2", date(2026, 7, 10), 7),
            LoadedKidEditPeriod(17, "w1", "Woche 1 (3 Tage)", date(2026, 7, 5), 3),
        )
        focuses = (
            LoadedKidEditFocusLink(17, 92, "alpha"),
            LoadedKidEditFocusLink(99, 999, "FOREIGN FOCUS SECRET"),
            LoadedKidEditFocusLink(17, 91, "Alpha"),
        )
        events = (
            LoadedKidEditEvent(44, 3, "Dienst 3", 9),
            LoadedKidEditEvent(42, 1, "Dienst 1", 7),
            LoadedKidEditEvent(43, 2, "Dienst 2", 8),
        )
        assignments = (
            LoadedKidEditAssignment(44, 6, "station", 81, " Abwasch ", 44),
            LoadedKidEditAssignment(99, 2, "station", 999,
                                    "FOREIGN STATION SECRET", 99),
            LoadedKidEditAssignment(43, 5, "excused"),
        )
        return periods, focuses, events, assignments

    def serialize(self, *, assignments=None):
        periods, focuses, events, loaded_assignments = self.loaded()
        return serialize_kid_edit_snapshot(
            child=self.child,
            active_periods=periods,
            focus_links=focuses,
            active_events=events,
            assignments=loaded_assignments if assignments is None else assignments,
        )

    def expected(self):
        return {
            "versions": {"edit": 4, "happy_cleaning_number": 3},
            "fields": dict(RAW_FIELDS),
            "happy_cleaning_number": 42,
            "swp": [
                {"period_id": 17, "period_code": "w1",
                 "period_label": "Woche 1 (3 Tage)", "start": "2026-07-05",
                 "duration_days": 3,
                 "focuses": [{"id": 91, "label": "Alpha"},
                             {"id": 92, "label": "alpha"}]},
                {"period_id": 18, "period_code": "w2", "period_label": "Woche 2",
                 "start": "2026-07-10", "duration_days": 7, "focuses": []},
            ],
            "happy_cleaning": [
                {"event_id": 42, "display_number": 1, "event_label": "Dienst 1",
                 "event_revision": 7, "assignment_version": 0,
                 "target": {"kind": "unassigned"}},
                {"event_id": 43, "display_number": 2, "event_label": "Dienst 2",
                 "event_revision": 8, "assignment_version": 5,
                 "target": {"kind": "excused"}},
                {"event_id": 44, "display_number": 3, "event_label": "Dienst 3",
                 "event_revision": 9, "assignment_version": 6,
                 "target": {"kind": "station", "station_id": 81,
                            "station_label": " Abwasch "}},
            ],
        }

    def test_complete_loaded_snapshot_is_exact_ordered_storage_faithful_and_query_free(self):
        with self.assertNumQueries(0):
            snapshot = self.serialize()
        self.assertEqual(snapshot, self.expected())
        assert_plain_json(self, snapshot)
        self.assertNotIn("FOREIGN", repr(snapshot))

    def test_result_is_new_deep_plain_json_and_loaded_dtos_are_frozen_redacted(self):
        periods, focuses, events, assignments = self.loaded()
        snapshot = self.serialize()
        snapshot["fields"]["illness"] = "mutated"
        snapshot["swp"][0]["focuses"][0]["label"] = "mutated"
        self.assertEqual(self.serialize(), self.expected())
        for item in (*periods, *focuses, *events, *assignments):
            self.assertNotIn("Alpha", repr(item))
            self.assertNotIn("SECRET", repr(item))
            with self.assertRaises(FrozenInstanceError):
                item.some_field = "mutated"

    def test_corrupt_cross_event_station_fails_closed_without_label_leak(self):
        _periods, _focuses, _events, assignments = self.loaded()
        corrupt = list(assignments)
        corrupt[0] = LoadedKidEditAssignment(
            44, 6, "station", 81, "TOP SECRET STATION", 43,
        )
        with self.assertNoLogs("budo_app.kid_edit_audit_snapshot"):
            with self.assertRaises(ValidationError) as raised:
                self.serialize(assignments=tuple(corrupt))
        self.assertNotIn("TOP SECRET", str(raised.exception))

    def test_builder_returns_validated_details_and_passes_expected_paths(self):
        self.assertTrue(callable(build_kid_edit_audit_details),
                        "audit detail builder is not implemented")
        before = self.serialize()
        after = deepcopy(before)
        after["versions"]["edit"] = 5
        after["fields"]["illness"] = "Nein"
        paths = ["illness"]
        with mock.patch.object(
            snapshot_module, "validate_kid_edit_details",
            wraps=snapshot_module.validate_kid_edit_details,
        ) as validator:
            result = build_kid_edit_audit_details(before, after, paths)
        self.assertEqual(result["before"], before)
        self.assertEqual(result["after"], after)
        self.assertEqual(result["changed_paths"], paths)
        validator.assert_called_once()
        self.assertEqual(
            validator.call_args.kwargs["expected_changed_paths"], paths,
        )


class KidEditFingerprintTests(SimpleTestCase):
    def command(self, *, field_overrides=None, reverse=False):
        fields = {
            field.storage_name: (
                date.fromisoformat(RAW_FIELDS[field.api_name])
                if field.api_name == "birthday" else RAW_FIELDS[field.api_name]
            )
            for field in FIELD_CONTRACTS
        }
        fields["kid_vorname"] = " TOP SECRET COMMAND "
        fields.update(field_overrides or {})
        items = list(fields.items())
        if reverse:
            items.reverse()
        swp = (
            ValidatedKidEditSwp(18, (), SwpTarget("unassigned")),
            ValidatedKidEditSwp(17, (91, 92), SwpTarget("focus", focus_id=91)),
        )
        happy = (
            ValidatedKidEditHappyCleaning(43, 5, HappyCleaningTarget("excused")),
            ValidatedKidEditHappyCleaning(42, 0, HappyCleaningTarget("unassigned")),
            ValidatedKidEditHappyCleaning(44, 6,
                                          HappyCleaningTarget("station", 81)),
        )
        if reverse:
            swp = tuple(reversed(swp))
            happy = tuple(reversed(happy))
        return ValidatedKidEditCommand(
            request_id="request-164", turnus_id=7, child_id=42,
            expected_edit_version=4, storage_fields=dict(items), swp=swp,
            happy_cleaning_number=12, expected_number_version=3,
            happy_cleaning=happy,
        )

    def require(self):
        self.assertTrue(callable(sign_kid_edit_command),
                        "kid-edit fingerprint signer is not implemented")
        self.assertTrue(callable(verify_kid_edit_command_fingerprint))

    @override_settings(SECRET_KEY="fingerprint-primary", SECRET_KEY_FALLBACKS=[])
    def test_exact_format_dedicated_salt_determinism_and_canonical_order(self):
        self.require()
        self.assertEqual(KID_EDIT_FINGERPRINT_SALT, FINGERPRINT_SALT)
        first = sign_kid_edit_command(self.command())
        reordered = sign_kid_edit_command(self.command(reverse=True))
        self.assertRegex(first, FINGERPRINT_PATTERN)
        self.assertEqual(len(first), 79)
        self.assertEqual(first, reordered)
        self.assertNotIn("TOP SECRET COMMAND", first)

    @override_settings(SECRET_KEY="fingerprint-primary", SECRET_KEY_FALLBACKS=[])
    def test_typed_complete_command_changes_digest_without_exposing_payload(self):
        self.require()
        fingerprints = {
            sign_kid_edit_command(self.command(field_overrides=overrides))
            for overrides in (
                {}, {"kid_vorname": "different"}, {"turnus_dauer": 8},
                {"budo_erfahrung": True}, {"geschwister": "present"},
            )
        }
        self.assertEqual(len(fingerprints), 5)
        with self.assertNoLogs("budo_app.kid_edit_fingerprint"):
            fingerprint = sign_kid_edit_command(self.command())
        self.assertNotIn("TOP SECRET", repr(fingerprint))
        self.assertNotIn("TOP SECRET", repr(self.command()))

    def test_secret_key_fallbacks_verify_and_all_keys_use_constant_time_compare(self):
        self.require()
        with override_settings(SECRET_KEY="old-key", SECRET_KEY_FALLBACKS=[]):
            old_fingerprint = sign_kid_edit_command(self.command())
        with override_settings(
            SECRET_KEY="new-key", SECRET_KEY_FALLBACKS=["old-key"],
        ):
            with mock.patch.object(
                fingerprint_module.secrets, "compare_digest",
                wraps=fingerprint_module.secrets.compare_digest,
            ) as compare:
                self.assertTrue(verify_kid_edit_command_fingerprint(
                    old_fingerprint, self.command(),
                ))
            self.assertEqual(compare.call_count, 2)

    @override_settings(SECRET_KEY="fingerprint-primary", SECRET_KEY_FALLBACKS=[])
    def test_malformed_wrong_payload_and_wrong_key_are_false(self):
        self.require()
        fingerprint = sign_kid_edit_command(self.command())
        for malformed in (
            "", "hmac-sha256:v1:", "hmac-sha256:v2:" + "a" * 64,
            "hmac-sha256:v1:" + "A" * 64, "hmac-sha256:v1:" + "a" * 63,
            None, b"fingerprint",
        ):
            with self.subTest(malformed=malformed):
                self.assertFalse(verify_kid_edit_command_fingerprint(
                    malformed, self.command(),
                ))
        self.assertFalse(verify_kid_edit_command_fingerprint(
            fingerprint, self.command(field_overrides={"kid_vorname": "different"}),
        ))
        with override_settings(SECRET_KEY="wrong-key", SECRET_KEY_FALLBACKS=[]):
            self.assertFalse(verify_kid_edit_command_fingerprint(
                fingerprint, self.command(),
            ))
