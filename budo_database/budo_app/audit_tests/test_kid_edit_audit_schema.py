"""RED contract for the sensitive ``kid.edit`` audit detail schema (#164-01)."""

from copy import deepcopy
from datetime import date
import json

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TransactionTestCase
from django.utils.functional import SimpleLazyObject

from budo_app.models import Turnus
from budo_app.audit import (
    MAX_DETAILS_BYTES,
    MAX_DETAIL_STRING,
    SENSITIVE_KEY_PARTS,
    AuditEventData,
    record_audit_event,
)

try:
    from budo_app.kid_edit_audit import (
        MAX_KID_EDIT_AUDIT_BYTES,
        validate_kid_edit_details,
    )
except ModuleNotFoundError as error:  # Keep discovery useful during the RED phase.
    if error.name != "budo_app.kid_edit_audit":
        raise
    MAX_KID_EDIT_AUDIT_BYTES = None
    validate_kid_edit_details = None


KID_EDIT_BYTE_LIMIT = 4 * 1024 * 1024
FIELD_NAMES = (
    "first_name", "last_name", "sex", "birthday", "stay_weeks",
    "siblings", "tent_request", "budo_experience",
    "social_security_number", "illness", "drugs", "vegetarian",
    "special_food", "swimmer", "consent",
    "over_the_counter_medication", "prescription_medication", "tetanus",
    "tick_vaccine", "organization", "registrant_first_name",
    "registrant_last_name", "registrant_email", "registrant_phone",
    "insured_with", "emergency_contacts", "budo_family",
)

# Literal audit-storage contract. This deliberately does not derive expectations
# from FIELD_CONTRACTS or model metadata: drift must break this test visibly.
# Tuple values are (JSON type, nullable, audit string limit).
STORAGE_FIELD_CONTRACT = {
    "first_name": ("string", False, 255),
    "last_name": ("string", False, 255),
    "sex": ("string", True, 255),
    "birthday": ("date", True, None),
    "stay_weeks": ("integer", True, None),
    "siblings": ("string", True, 255),
    "tent_request": ("string", True, 255),
    "budo_experience": ("boolean", True, None),
    "social_security_number": ("string", True, 255),
    "illness": ("string", True, 10_000),
    "drugs": ("string", True, 10_000),
    "vegetarian": ("string", True, 255),
    "special_food": ("string", True, 255),
    "swimmer": ("string", True, 255),
    "consent": ("boolean", True, None),
    "over_the_counter_medication": ("string", True, 10_000),
    "prescription_medication": ("string", True, 255),
    "tetanus": ("string", True, 255),
    "tick_vaccine": ("string", True, 255),
    "organization": ("string", True, 255),
    "registrant_first_name": ("string", False, 255),
    "registrant_last_name": ("string", False, 255),
    "registrant_email": ("string", True, 255),
    "registrant_phone": ("string", True, 255),
    "insured_with": ("string", True, 255),
    "emergency_contacts": ("string", True, 10_000),
    "budo_family": ("string", True, 30),
}
POSTGRES_INTEGER_MIN = -2_147_483_648
POSTGRES_INTEGER_MAX = 2_147_483_647
POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807
BASELINE_TOKEN = "v1." + "A" * 43
LEGACY_BASELINE_TOKEN = "legacy:v1." + "B" * 43


class CustomDetailsMapping(dict):
    """A Mapping that must not cross the strict plain-JSON boundary."""


def _fields(*, after=False):
    values = {
        "first_name": " Ada ", "last_name": "", "sex": "LEGACY-sex",
        "birthday": "2012-07-02", "stay_weeks": 7, "siblings": None,
        "tent_request": "  Bea\nGrace  ", "budo_experience": None,
        "social_security_number": " 0207 121234 ", "illness": "nein",
        "drugs": "", "vegetarian": "LEGACY-Veg", "special_food": None,
        "swimmer": "Gut", "consent": False,
        "over_the_counter_medication": "  Bei Bedarf\n  ",
        "prescription_medication": None, "tetanus": "", "tick_vaccine": None,
        "organization": "Org", "registrant_first_name": " Augusta ",
        "registrant_last_name": "Lovelace", "registrant_email": " Invalid@ ",
        "registrant_phone": "+43 660", "insured_with": None,
        "emergency_contacts": "Charles\n+43", "budo_family": "LEGACY",
    }
    if after:
        values["illness"] = "Nein"
    return values


def _periods(*, after=False):
    return [
        {
            "period_id": 17, "period_code": "w1",
            "period_label": "Woche 1 (3 Tage)", "start": "2026-07-05",
            "duration_days": 3,
            "focuses": ([
                {"id": 91, "label": "Alpha"},
                {"id": 92, "label": "alpha"},
            ] if after else []),
        },
        {
            "period_id": 18, "period_code": "w2",
            "period_label": "Woche 2", "start": "2026-07-10",
            "duration_days": 7,
            "focuses": [{"id": 93, "label": "Theater"}],
        },
    ]


def _happy_cleaning(*, after=False):
    first = {
        "event_id": 42, "display_number": 1, "event_label": "Dienst 1",
        "event_revision": 18 if after else 17,
        "assignment_version": 19 if after else 0,
        "target": ({"kind": "station", "station_id": 9,
                    "station_label": "Küche <Nord>"}
                   if after else {"kind": "unassigned"}),
    }
    return [
        first,
        {"event_id": 43, "display_number": 2, "event_label": "Dienst 2",
         "event_revision": 6, "assignment_version": 6,
         "target": {"kind": "excused"}},
        {"event_id": 44, "display_number": 3, "event_label": "Dienst 3",
         "event_revision": 3, "assignment_version": 3,
         "target": {"kind": "station", "station_id": 8,
                    "station_label": "Abwasch"}},
        {"event_id": 45, "display_number": 4, "event_label": "Dienst 4",
         "event_revision": 2, "assignment_version": 0,
         "target": {"kind": "unassigned"}},
    ]


def valid_details():
    return {
        "schema": "budo.kid-edit", "version": 1, "result": "updated",
        "changed_paths": [
            "illness", "swp.17", "happy_cleaning_number",
            "happy_cleaning.42",
        ],
        "before": {
            "versions": {"edit": 4, "happy_cleaning_number": 3},
            "fields": _fields(), "happy_cleaning_number": 42,
            "swp": _periods(), "happy_cleaning": _happy_cleaning(),
        },
        "after": {
            "versions": {"edit": 5, "happy_cleaning_number": 4},
            "fields": _fields(after=True), "happy_cleaning_number": 43,
            "swp": _periods(after=True),
            "happy_cleaning": _happy_cleaning(after=True),
        },
    }


def set_both_field_values(details, name, value):
    """Exercise storage validation without introducing a domain-diff signal."""
    details["before"]["fields"][name] = value
    details["after"]["fields"][name] = value


def set_both_relationship_labels(details, location, value):
    for snapshot in ("before", "after"):
        if location == "period":
            details[snapshot]["swp"][0]["period_label"] = value
        elif location == "focus":
            details[snapshot]["swp"][1]["focuses"][0]["label"] = value
        elif location == "event":
            details[snapshot]["happy_cleaning"][2]["event_label"] = value
        elif location == "station":
            details[snapshot]["happy_cleaning"][2]["target"][
                "station_label"
            ] = value
        else:  # pragma: no cover - test helper programming error
            raise AssertionError(location)


def encoded_size(value):
    return len(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))


def details_at_exact_size(target):
    """Construct a schema-valid detail object of exactly ``target`` UTF-8 bytes."""
    details = valid_details()
    focuses = details["after"]["swp"][0]["focuses"]
    fixed = deepcopy(focuses)

    def fill(count):
        focuses[:] = fixed + [
            {"id": 1000 + index,
             "label": f"z{index:08d}" + "x" * (255 - 9)}
            for index in range(count)
        ]
        return encoded_size(details)

    low, high = 0, 20_000
    while low < high:
        middle = (low + high + 1) // 2
        if fill(middle) <= target:
            low = middle
        else:
            high = middle - 1
    current = fill(low)
    if current == target:
        return details

    remainder = target - current
    filler_id = 1000 + low
    focuses.append({"id": filler_id, "label": "zz"})
    minimum_delta = encoded_size(details) - current
    focuses.pop()
    if remainder < minimum_delta:
        # Free exactly enough bytes while retaining lexical focus order.
        shortage = minimum_delta - remainder
        focuses[-1]["label"] = focuses[-1]["label"][:-shortage]
        current -= shortage
        remainder = target - current
    filler_length = 2 + remainder - minimum_delta
    focuses.append({"id": filler_id, "label": "z" * filler_length})
    assert encoded_size(details) == target
    return details


class KidEditDetailSchemaTests(SimpleTestCase):
    def validate(self, value, **kwargs):
        self.assertTrue(callable(validate_kid_edit_details),
                        "budo_app.kid_edit_audit is not implemented yet")
        return validate_kid_edit_details(value, **kwargs)

    def assert_invalid(self, value):
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_complete_example_is_accepted_and_reconstructed_as_plain_json(self):
        source = valid_details()
        result = self.validate(source)
        self.assertEqual(result, source)
        self.assertIsNot(result, source)
        self.assertIsNot(result["before"], source["before"])
        self.assertIs(type(result), dict)
        self.assertIs(type(result["before"]["swp"]), list)
        self.assertEqual(tuple(result["before"]["fields"]), FIELD_NAMES)
        self.assertEqual(
            json.dumps(result, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")),
            json.dumps(self.validate(deepcopy(source)), ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")),
        )

    def test_raw_incidental_differences_do_not_define_changed_paths(self):
        details = valid_details()
        details["after"]["fields"]["sex"] = "another legacy spelling"
        details["after"]["fields"]["organization"] = "incidental raw change"

        result = self.validate(details)

        self.assertEqual(result["changed_paths"], details["changed_paths"])

    def test_producer_plan_can_require_exact_changed_path_equality_and_order(self):
        details = valid_details()
        expected = list(details["changed_paths"])
        self.validate(details, expected_changed_paths=expected)
        for mismatch in (
            expected[:-1],
            [*expected, "first_name"],
            list(reversed(expected)),
        ):
            with self.subTest(mismatch=mismatch), self.assertRaises(ValidationError):
                self.validate(details, expected_changed_paths=mismatch)

    def test_literal_storage_contract_covers_all_27_fields_in_wire_order(self):
        self.assertEqual(tuple(STORAGE_FIELD_CONTRACT), FIELD_NAMES)

    def test_every_string_field_enforces_exact_limit_and_model_nullability(self):
        for name, (kind, nullable, maximum) in STORAGE_FIELD_CONTRACT.items():
            if kind != "string":
                continue
            at_limit = valid_details()
            set_both_field_values(at_limit, name, "x" * maximum)
            if name == "illness":
                at_limit["after"]["fields"][name] = "y" * maximum
            with self.subTest(field=name, case="at limit"):
                self.validate(at_limit)

            over_limit = valid_details()
            set_both_field_values(over_limit, name, "x" * (maximum + 1))
            with self.subTest(field=name, case="over limit"):
                self.assert_invalid(over_limit)

            null_value = valid_details()
            set_both_field_values(null_value, name, None)
            if name == "illness":
                null_value["after"]["fields"][name] = ""
            with self.subTest(field=name, case="null", nullable=nullable):
                if nullable:
                    self.validate(null_value)
                else:
                    self.assert_invalid(null_value)

            if not nullable:
                empty_value = valid_details()
                set_both_field_values(empty_value, name, "")
                with self.subTest(field=name, case="empty non-null storage"):
                    self.validate(empty_value)

    def test_storage_dates_booleans_and_integer_bounds_are_exact(self):
        for field in ("birthday",):
            for value in (None, "0001-01-01", "9999-12-31"):
                details = valid_details()
                set_both_field_values(details, field, value)
                with self.subTest(field=field, accepted=value):
                    self.validate(details)
            for value in ("2012-2-03", "2012-02-30", "2012-02-03T00:00:00", 1):
                details = valid_details()
                set_both_field_values(details, field, value)
                with self.subTest(field=field, rejected=value):
                    self.assert_invalid(details)

        for field in ("budo_experience", "consent"):
            for value in (None, True, False):
                details = valid_details()
                set_both_field_values(details, field, value)
                with self.subTest(field=field, accepted=value):
                    self.validate(details)
            for value in (0, 1, "true"):
                details = valid_details()
                set_both_field_values(details, field, value)
                with self.subTest(field=field, rejected=value):
                    self.assert_invalid(details)

        for value in (None, POSTGRES_INTEGER_MIN, POSTGRES_INTEGER_MAX):
            details = valid_details()
            set_both_field_values(details, "stay_weeks", value)
            with self.subTest(stay_weeks_accepted=value):
                self.validate(details)
        for value in (
            POSTGRES_INTEGER_MIN - 1, POSTGRES_INTEGER_MAX + 1,
            True, False, 1.0, float("nan"),
        ):
            details = valid_details()
            set_both_field_values(details, "stay_weeks", value)
            with self.subTest(stay_weeks_rejected=repr(value)):
                self.assert_invalid(details)

    def test_period_start_rejects_null_mixed_and_malformed_with_validation_error(self):
        for snapshot, index, value in (
            ("before", 0, None),
            ("after", 1, None),
            ("before", 0, "2026-7-05"),
            ("after", 1, "2026-02-30"),
            ("before", 0, 20260705),
        ):
            details = valid_details()
            details[snapshot]["swp"][index]["start"] = value
            with self.subTest(snapshot=snapshot, index=index, value=value):
                # Specifically requires ValidationError, not a leaked sort TypeError.
                self.assert_invalid(details)

    def test_non_json_and_opaque_values_are_rejected(self):
        mutations = []
        for value in (
            1.5, float("nan"), b"Ada", ("Ada",),
            SimpleLazyObject(lambda: "Ada"),
        ):
            details = valid_details()
            set_both_field_values(details, "first_name", value)
            mutations.append((repr(value), details))
        mutations.append(("custom mapping", CustomDetailsMapping(valid_details())))
        for label, details in mutations:
            with self.subTest(label=label):
                self.assert_invalid(details)

    def test_baseline_token_syntax_is_rejected_in_every_string_scalar(self):
        string_fields = [
            name for name, (kind, _nullable, _maximum)
            in STORAGE_FIELD_CONTRACT.items() if kind == "string"
        ]
        for name in string_fields:
            for token in (BASELINE_TOKEN, LEGACY_BASELINE_TOKEN):
                details = valid_details()
                set_both_field_values(details, name, token)
                with self.subTest(field=name, prefix=token.split(".", 1)[0]):
                    self.assert_invalid(details)

    def test_token_like_but_non_token_raw_scalar_strings_are_preserved(self):
        string_fields = [
            name for name, (kind, _nullable, _maximum)
            in STORAGE_FIELD_CONTRACT.items() if kind == "string"
        ]
        for name in string_fields:
            for raw in ("v1.A", "legacy:v1.B"):
                details = valid_details()
                set_both_field_values(details, name, raw)
                with self.subTest(field=name, raw=raw):
                    result = self.validate(details)
                    self.assertEqual(result["before"]["fields"][name], raw)
                    self.assertEqual(result["after"]["fields"][name], raw)

    def test_baseline_tokens_are_rejected_in_relationship_labels_only_exactly(self):
        for location in ("period", "focus", "event", "station"):
            for token in (BASELINE_TOKEN, LEGACY_BASELINE_TOKEN):
                details = valid_details()
                set_both_relationship_labels(details, location, token)
                with self.subTest(location=location, token=token[:9]):
                    self.assert_invalid(details)
            for raw in ("v1.A", "legacy:v1.B"):
                details = valid_details()
                set_both_relationship_labels(details, location, raw)
                with self.subTest(location=location, raw=raw):
                    self.validate(details)

    def test_storage_blank_period_code_focus_and_station_labels_are_reconstructed(self):
        for location in ("period_code", "focus", "station"):
            details = valid_details()
            if location == "period_code":
                for snapshot in ("before", "after"):
                    details[snapshot]["swp"][0]["period_code"] = ""
            else:
                set_both_relationship_labels(details, location, "")
            with self.subTest(location=location):
                result = self.validate(details)
                for snapshot in ("before", "after"):
                    if location == "period_code":
                        actual = result[snapshot]["swp"][0]["period_code"]
                    elif location == "focus":
                        actual = result[snapshot]["swp"][1]["focuses"][0][
                            "label"
                        ]
                    else:
                        actual = result[snapshot]["happy_cleaning"][2][
                            "target"
                        ]["station_label"]
                    self.assertEqual(actual, "")

    def test_exact_top_snapshot_and_27_field_keysets_are_required(self):
        cases = []
        for level, required in (
            ((), "schema"), (("before",), "versions"),
            (("after",), "versions"),
            (("before", "fields"), "first_name"),
            (("after", "fields"), "first_name"),
            (("before", "swp", 0), "period_id"),
            (("after", "swp", 0, "focuses", 0), "id"),
            (("before", "happy_cleaning", 0), "event_id"),
            (("before", "happy_cleaning", 0, "target"), "kind"),
        ):
            missing = valid_details()
            node = missing
            for key in level:
                node = node[key]
            node.pop(required)
            cases.append((f"missing {level!r}.{required}", missing))
            extra = valid_details()
            node = extra
            for key in level:
                node = node[key]
            node["unknown"] = None
            cases.append((f"unknown at {level!r}", extra))
        wrong_count = valid_details()
        wrong_count["after"]["fields"].pop("budo_family")
        cases.append(("not 27 fields", wrong_count))
        for label, details in cases:
            with self.subTest(label):
                self.assert_invalid(details)

    def test_representative_swp_hc_target_version_and_json_type_invariants(self):
        mutations = []
        for path, value in (
            (("before", "versions", "edit"), True),
            (("before", "versions", "edit"), 0),
            (("before", "happy_cleaning_number"), -1),
            (("before", "fields", "stay_weeks"), 1.5),
            (("before", "fields", "birthday"), "2012-2-03"),
            (("before", "swp", 0, "period_id"), True),
            (("before", "swp", 0, "duration_days"), 0),
            (("before", "swp", 0, "focuses"), tuple()),
            (("before", "happy_cleaning", 0, "event_revision"), 0),
            (("before", "happy_cleaning", 0, "assignment_version"), 2),
            (("before", "happy_cleaning", 1, "assignment_version"), 0),
            (("before", "happy_cleaning", 2, "target", "station_id"), False),
        ):
            details = valid_details()
            node = details
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            mutations.append((path, details))
        non_string_key = valid_details()
        non_string_key["before"][1] = "not JSON"
        mutations.append((("before", 1), non_string_key))
        unknown_target_key = valid_details()
        unknown_target_key["before"]["happy_cleaning"][2]["target"]["token"] = "x"
        mutations.append((("target", "unknown key"), unknown_target_key))
        missing_target_key = valid_details()
        missing_target_key["before"]["happy_cleaning"][2]["target"].pop(
            "station_label"
        )
        mutations.append((("target", "missing key"), missing_target_key))
        for path, details in mutations:
            with self.subTest(path=path):
                self.assert_invalid(details)

    def test_period_and_event_sets_must_be_equal_unique_and_ordered(self):
        for label, mutate in (
            ("period order", lambda d: d["after"]["swp"].reverse()),
            ("period set", lambda d: d["after"]["swp"].pop()),
            ("event order", lambda d: d["after"]["happy_cleaning"].reverse()),
            ("event set", lambda d: d["after"]["happy_cleaning"].pop()),
        ):
            details = valid_details()
            mutate(details)
            with self.subTest(label):
                self.assert_invalid(details)

    def test_changed_paths_are_nonempty_unique_valid_and_canonically_ordered(self):
        for paths in (
            [], ["illness", "illness"], ["unknown"], ["swp.999"],
            ["happy_cleaning.999"], ["swp.17", "illness"],
            ["happy_cleaning.42", "happy_cleaning_number"],
        ):
            details = valid_details()
            details["changed_paths"] = paths
            with self.subTest(paths=paths):
                self.assert_invalid(details)

    def test_dedicated_limit_is_actual_utf8_four_mib_inclusive(self):
        at_limit = details_at_exact_size(KID_EDIT_BYTE_LIMIT)
        self.assertEqual(encoded_size(at_limit), KID_EDIT_BYTE_LIMIT)
        self.assertEqual(MAX_KID_EDIT_AUDIT_BYTES, KID_EDIT_BYTE_LIMIT)
        self.validate(at_limit)
        over_limit = deepcopy(at_limit)
        over_limit["before"]["fields"]["illness"] += "x"
        self.assertEqual(encoded_size(over_limit), KID_EDIT_BYTE_LIMIT + 1)
        self.assert_invalid(over_limit)


class KidEditAuditDispatchTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=164, turnus_beginn=date(2026, 7, 1),
        )

    def event(self, **changes):
        values = dict(
            turnus=self.turnus, actor_id=None, actor_label="System",
            action="kid.edit", outcome="success",
            resource_type="child", resource_id="42", resource_label="Ada",
            request_id="request-kid-edit", client_ip=None, user_agent="tests",
            details=valid_details(),
        )
        values.update(changes)
        return AuditEventData(**values)

    def test_exact_outer_action_outcome_and_decimal_child_id_dispatch_schema(self):
        created = record_audit_event(self.event())
        self.assertEqual(created.details, valid_details())
        for changes in (
            {"outcome": "forbidden"},
            {"resource_type": "turnus"}, {"resource_id": "0"},
            {"resource_id": "01"}, {"resource_id": "1.0"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                record_audit_event(self.event(**changes))

    def test_child_resource_id_accepts_signed_bigint_max_and_rejects_plus_one(self):
        maximum = str(POSTGRES_BIGINT_MAX)
        created = record_audit_event(self.event(
            resource_id=maximum,
            request_id="request-kid-edit-bigint-max",
        ))
        self.assertEqual(created.resource_id, maximum)

        with self.assertRaises(ValidationError):
            record_audit_event(self.event(
                resource_id=str(POSTGRES_BIGINT_MAX + 1),
                request_id="request-kid-edit-bigint-overflow",
            ))


class LegacyAuditValidatorRegressionTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=164, turnus_beginn=date(2026, 7, 1),
        )

    def legacy_event(self, details):
        return AuditEventData(
            turnus=self.turnus, actor_id=None, actor_label="System",
            action="happy_cleaning.station.copy",
            outcome="success", resource_type="station",
            resource_id="9", resource_label="Abwasch", details=details,
            request_id="request-legacy", client_ip=None, user_agent="tests",
        )

    def test_generic_constants_and_sensitive_key_parts_are_unchanged(self):
        self.assertEqual(MAX_DETAILS_BYTES, 4096)
        self.assertEqual(MAX_DETAIL_STRING, 500)
        self.assertEqual(SENSITIVE_KEY_PARTS, {
            "body", "cookie", "token", "password", "secret", "health",
            "illness", "drug", "contact", "phone", "email", "money",
            "amount", "allerg", "address", "sozialversicher",
        })

    def test_generic_four_kib_string_list_depth_and_sensitive_controls_remain(self):
        accepted = {"station_copy_decisions": ["x" * 70] * 50}
        oversized = {"station_copy_decisions": ["x" * 90] * 50}
        self.assertLess(encoded_size(accepted), 4096)
        self.assertGreater(encoded_size(oversized), 4096)
        record_audit_event(self.legacy_event(accepted))
        record_audit_event(self.legacy_event(
            {"station_copy_decisions": [{"safe": ["x" * 500]}]}
        ))
        for details in (
            oversized,
            {"station_copy_decisions": ["x"] * 51},
            {"station_copy_decisions": [{"safe": [["too deep"]]}]},
            {"station_copy_decisions": [{"safe": ["x" * 501]}]},
            {"station_copy_decisions": [{"illness_note": "no"}]},
        ):
            with self.subTest(details=details), self.assertRaises(ValidationError):
                record_audit_event(self.legacy_event(details))
