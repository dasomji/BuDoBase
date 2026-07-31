from dataclasses import FrozenInstanceError
from datetime import date

from django.test import SimpleTestCase


EMPTY_DEFAULT = frozenset({"nein", "nan", "none", "-"})
EMPTY_REQUEST = EMPTY_DEFAULT | {"0", "/", "bein"}
EMPTY_FOOD = frozenset({"nein", "keine", "keinr", "nan", "ja"})


EXPECTED_FIELDS = (
    # api, storage, kind, limit, multiline, required, blanks, clear, mappings
    ("first_name", "kid_vorname", "text", 255, False, True, (), None, ()),
    ("last_name", "kid_nachname", "text", 255, False, True, (), None, ()),
    (
        "sex",
        "sex",
        "enum",
        None,
        False,
        False,
        ("", "-", "nan", "none"),
        None,
        (("female", "weiblich"), ("male", "männlich"), ("diverse", "divers")),
    ),
    ("birthday", "kid_birthday", "date", None, False, False, (), None, ()),
    (
        "stay_weeks",
        "turnus_dauer",
        "integer",
        None,
        False,
        False,
        (),
        None,
        ((1, 1), (2, 2)),
    ),
    (
        "siblings",
        "geschwister",
        "text",
        255,
        False,
        False,
        tuple(sorted(EMPTY_REQUEST)),
        None,
        (),
    ),
    (
        "tent_request",
        "zeltwunsch",
        "text",
        255,
        True,
        False,
        tuple(sorted(EMPTY_REQUEST)),
        None,
        (),
    ),
    (
        "budo_experience",
        "budo_erfahrung",
        "boolean",
        None,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "social_security_number",
        "sozialversicherungsnr",
        "text",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "illness",
        "illness",
        "text",
        10_000,
        True,
        False,
        tuple(sorted(EMPTY_DEFAULT)),
        None,
        (),
    ),
    (
        "drugs",
        "drugs",
        "text",
        10_000,
        True,
        False,
        tuple(sorted(EMPTY_DEFAULT)),
        None,
        (),
    ),
    (
        "vegetarian",
        "vegetarisch",
        "enum",
        None,
        False,
        False,
        ("", "-", "nan", "none"),
        None,
        ((True, "ja"), (False, "nein")),
    ),
    (
        "special_food",
        "special_food_description",
        "text",
        255,
        True,
        False,
        tuple(sorted(EMPTY_FOOD)),
        None,
        (),
    ),
    ("swimmer", "swimmer", "text", 255, False, False, (), None, ()),
    (
        "consent",
        "einverstaendnis_erklaerung",
        "boolean",
        None,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "over_the_counter_medication",
        "rezeptfreie_medikamente",
        "text",
        10_000,
        True,
        False,
        (),
        None,
        (),
    ),
    (
        "prescription_medication",
        "rezept_medikamente",
        "text",
        255,
        True,
        False,
        (),
        None,
        (),
    ),
    ("tetanus", "tetanusimpfung", "text", 255, False, False, (), None, ()),
    (
        "tick_vaccine",
        "zeckenimpfung",
        "text",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "organization",
        "anmelde_organisation",
        "text",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "registrant_first_name",
        "anmelder_vorname",
        "text",
        255,
        False,
        False,
        (),
        "",
        (),
    ),
    (
        "registrant_last_name",
        "anmelder_nachname",
        "text",
        255,
        False,
        False,
        (),
        "",
        (),
    ),
    (
        "registrant_email",
        "anmelder_email",
        "email",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "registrant_phone",
        "anmelder_mobil",
        "text",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "insured_with",
        "hauptversichert_bei",
        "text",
        255,
        False,
        False,
        (),
        None,
        (),
    ),
    (
        "emergency_contacts",
        "notfall_kontakte",
        "text",
        10_000,
        True,
        False,
        (),
        None,
        (),
    ),
    (
        "budo_family",
        "budo_family",
        "enum",
        None,
        False,
        False,
        ("",),
        None,
        (("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL")),
    ),
)


OPTIONAL_TEXT_EMAIL_CLEAR_MATRIX = (
    # API field, empty-string storage representation
    ("siblings", None),
    ("tent_request", None),
    ("social_security_number", None),
    ("illness", None),
    ("drugs", None),
    ("special_food", None),
    ("swimmer", None),
    ("over_the_counter_medication", None),
    ("prescription_medication", None),
    ("tetanus", None),
    ("tick_vaccine", None),
    ("organization", None),
    ("registrant_first_name", ""),
    ("registrant_last_name", ""),
    ("registrant_email", None),
    ("registrant_phone", None),
    ("insured_with", None),
    ("emergency_contacts", None),
)


class KidEditContractTests(SimpleTestCase):
    @staticmethod
    def public_contract():
        from budo_app.kid_edit_contracts import (
            FIELD_CONTRACTS,
            HAPPY_CLEANING_NUMBER_CONTRACT,
            KidEditContractError,
            canonicalize_storage_value,
            canonicalize_submission_value,
            is_canonical_no_op,
        )

        return (
            FIELD_CONTRACTS,
            HAPPY_CLEANING_NUMBER_CONTRACT,
            KidEditContractError,
            canonicalize_storage_value,
            canonicalize_submission_value,
            is_canonical_no_op,
        )

    def fields(self):
        return {field.api_name: field for field in self.public_contract()[0]}

    def assert_contract_error(self, field, value, code):
        error_type = self.public_contract()[2]
        canonicalize = self.public_contract()[4]
        with self.assertRaises(error_type) as raised:
            canonicalize(field, value)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(getattr(raised.exception, "details", {}), {})

    def test_exact_immutable_ordered_field_metadata_and_compatibility_export(self):
        contracts = self.public_contract()[0]
        actual = tuple(
            (
                field.api_name,
                field.storage_name,
                field.value_type,
                field.max_length,
                field.multiline,
                field.required,
                tuple(sorted(field.semantic_blanks)),
                field.clear_storage_value,
                tuple(field.api_to_storage),
            )
            for field in contracts
        )
        self.assertEqual(actual, EXPECTED_FIELDS)
        self.assertEqual(len(contracts), 27)
        with self.assertRaises(FrozenInstanceError):
            contracts[0].required = False

        from budo_app.kid_edit_writes import COVERED_KINDER_FIELDS

        self.assertEqual(
            tuple(COVERED_KINDER_FIELDS),
            tuple(field.storage_name for field in contracts),
        )

    def test_happy_cleaning_number_is_separate_from_the_27_fields(self):
        fields, number, *_rest = self.public_contract()
        self.assertNotIn(
            "happy_cleaning_number",
            tuple(field.api_name for field in fields),
        )
        self.assertEqual(number.api_name, "happy_cleaning_number")
        self.assertEqual(number.storage_name, "happy_cleaning_number")
        self.assertEqual(number.value_type, "integer")
        self.assertEqual(number.minimum, 1)
        self.assertEqual(number.maximum, 2_147_483_647)
        self.assertFalse(number.required)
        with self.assertRaises(FrozenInstanceError):
            number.minimum = 0

    def test_text_normalizes_line_endings_unicode_trim_and_keeps_layout(self):
        canonicalize = self.public_contract()[4]
        fields = self.fields()
        result = canonicalize(
            fields["illness"],
            "\u2003First\r\nSecond\rThird\titem\u2002",
        )
        self.assertEqual(result.api_value, "First\nSecond\nThird\titem")
        self.assertEqual(result.storage_value, "First\nSecond\nThird\titem")

    def test_controls_and_single_line_breaks_are_rejected(self):
        fields = self.fields()
        for value in ("Ada\x00", "Ada\x01", "Ada\x1f"):
            with self.subTest(value=repr(value)):
                self.assert_contract_error(fields["first_name"], value, "control")
        for value in ("Ada\nLovelace", "Ada\tLovelace", "Ada\rLovelace"):
            with self.subTest(value=repr(value)):
                self.assert_contract_error(
                    fields["first_name"],
                    value,
                    "single_line",
                )
        self.assertEqual(
            self.public_contract()[4](fields["emergency_contacts"], "A\n\tB").api_value,
            "A\n\tB",
        )

    def test_limits_apply_after_normalization(self):
        fields = self.fields()
        canonicalize = self.public_contract()[4]
        self.assertEqual(
            len(canonicalize(fields["first_name"], " " + "x" * 255 + " ").api_value),
            255,
        )
        self.assert_contract_error(fields["first_name"], "x" * 256, "too_long")
        self.assertEqual(
            len(canonicalize(fields["illness"], "x" * 10_000).api_value),
            10_000,
        )
        self.assert_contract_error(fields["illness"], "x" * 10_001, "too_long")

    def test_field_specific_semantic_blank_families(self):
        read = self.public_contract()[3]
        fields = self.fields()
        families = (
            (("illness", "drugs"), EMPTY_DEFAULT),
            (("siblings", "tent_request"), EMPTY_REQUEST),
            (("special_food",), EMPTY_FOOD),
        )
        for names, values in families:
            for name in names:
                for value in values:
                    with self.subTest(field=name, value=value):
                        result = read(fields[name], f"  {value.upper()}  ")
                        self.assertEqual(result.api_value, "")
                        self.assertEqual(result.storage_value, f"  {value.upper()}  ")
        self.assertEqual(read(fields["swimmer"], "nein").api_value, "nein")
        self.assertIs(read(fields["vegetarian"], "nein").api_value, False)

    def test_controlled_storage_and_api_mappings(self):
        read = self.public_contract()[3]
        submit = self.public_contract()[4]
        fields = self.fields()
        storage_cases = (
            ("sex", " WEIBLICH ", "female"),
            ("sex", "MÄNNLICH", "male"),
            ("sex", "Divers", "diverse"),
            ("vegetarian", " JA ", True),
            ("vegetarian", "nein", False),
            ("budo_family", "XL", "XL"),
            ("stay_weeks", 2, 2),
        )
        for name, raw, expected in storage_cases:
            with self.subTest(field=name, raw=raw):
                self.assertEqual(read(fields[name], raw).api_value, expected)
        submission_cases = (
            ("sex", "female", "weiblich"),
            ("sex", "male", "männlich"),
            ("sex", "diverse", "divers"),
            ("vegetarian", True, "ja"),
            ("vegetarian", False, "nein"),
            ("budo_family", "M", "M"),
            ("stay_weeks", 1, 1),
        )
        for name, api_value, storage_value in submission_cases:
            with self.subTest(field=name, value=api_value):
                self.assertEqual(
                    submit(fields[name], api_value).storage_value,
                    storage_value,
                )

    def test_unknown_controlled_and_invalid_email_return_preservation_signals(self):
        read = self.public_contract()[3]
        fields = self.fields()
        for name, raw in (
            ("sex", "legacy-sex"),
            ("vegetarian", "vielleicht"),
            ("budo_family", "XXL"),
            ("stay_weeks", 3),
        ):
            with self.subTest(field=name):
                result = read(fields[name], raw)
                self.assertEqual(result.api_value, raw)
                self.assertTrue(result.preserve_raw)
                self.assertEqual(result.legacy_kind, "unknown_choice")
        email = read(fields["registrant_email"], "  ada@  ")
        self.assertEqual(email.api_value, "ada@")
        self.assertTrue(email.preserve_raw)
        self.assertEqual(email.legacy_kind, "invalid_email")

    def test_boolean_date_null_and_required_types_are_exact(self):
        submit = self.public_contract()[4]
        fields = self.fields()
        self.assertIsNone(submit(fields["birthday"], None).storage_value)
        self.assertEqual(
            submit(fields["birthday"], "2012-02-29").storage_value,
            date(2012, 2, 29),
        )
        self.assert_contract_error(fields["birthday"], "2012-02-30", "invalid_date")
        for name in ("budo_experience", "consent"):
            for value in (True, False, None):
                self.assertIs(submit(fields[name], value).storage_value, value)
            self.assert_contract_error(fields[name], 1, "invalid_type")
        self.assert_contract_error(fields["stay_weeks"], True, "invalid_type")
        self.assert_contract_error(fields["first_name"], " \u2003 ", "required")
        self.assert_contract_error(fields["last_name"], None, "invalid_type")

    def test_every_optional_text_and_email_rejects_json_null(self):
        contracts = self.public_contract()[0]
        fields = self.fields()
        expected_names = tuple(
            name for name, _clear_storage in OPTIONAL_TEXT_EMAIL_CLEAR_MATRIX
        )
        actual_names = tuple(
            field.api_name
            for field in contracts
            if field.value_type in {"text", "email"} and not field.required
        )
        self.assertEqual(actual_names, expected_names)

        for name in expected_names:
            with self.subTest(field=name):
                self.assert_contract_error(fields[name], None, "invalid_type")

    def test_every_optional_text_and_email_clears_via_normalized_empty_string(self):
        submit = self.public_contract()[4]
        fields = self.fields()
        for name, expected_storage in OPTIONAL_TEXT_EMAIL_CLEAR_MATRIX:
            with self.subTest(field=name):
                result = submit(fields[name], " \u2003 ")
                self.assertEqual(result.api_value, "")
                self.assertEqual(result.storage_value, expected_storage)

    def test_invalid_submission_choices_and_email_are_rejected(self):
        fields = self.fields()
        for name, value in (
            ("sex", "weiblich"),
            ("vegetarian", "ja"),
            ("budo_family", "s"),
            ("budo_family", "xL"),
            ("budo_family", "XXL"),
            ("stay_weeks", 3),
        ):
            with self.subTest(field=name):
                self.assert_contract_error(fields[name], value, "invalid_choice")
        self.assert_contract_error(
            fields["registrant_email"],
            "ada@",
            "invalid_email",
        )

    def test_canonical_no_ops_preserve_raw_storage(self):
        no_op = self.public_contract()[5]
        fields = self.fields()
        cases = (
            ("illness", None, ""),
            ("illness", "", ""),
            ("illness", "nein", ""),
            ("first_name", " Ada ", "Ada"),
            ("registrant_email", " ada@ ", "ada@"),
            ("vegetarian", "NEIN", False),
        )
        for name, raw, submitted in cases:
            with self.subTest(field=name, raw=raw):
                self.assertTrue(no_op(fields[name], raw, submitted))
        self.assertFalse(no_op(fields["illness"], "nein", "Asthma"))
        self.assertFalse(no_op(fields["first_name"], "Ada", ""))

    def test_budo_family_storage_and_no_op_comparison_are_exact_case(self):
        read = self.public_contract()[3]
        no_op = self.public_contract()[5]
        field = self.fields()["budo_family"]

        for exact_choice in ("S", "M", "L", "XL"):
            with self.subTest(exact_choice=exact_choice):
                result = read(field, exact_choice)
                self.assertEqual(result.api_value, exact_choice)
                self.assertFalse(result.preserve_raw)
                self.assertIsNone(result.legacy_kind)
                self.assertTrue(no_op(field, exact_choice, exact_choice))

        for legacy_value in ("s", "m", "l", "xl", "xL"):
            with self.subTest(legacy_value=legacy_value):
                result = read(field, legacy_value)
                self.assertEqual(result.api_value, legacy_value)
                self.assertTrue(result.preserve_raw)
                self.assertEqual(result.legacy_kind, "unknown_choice")

        self.assertFalse(no_op(field, "s", "S"))
