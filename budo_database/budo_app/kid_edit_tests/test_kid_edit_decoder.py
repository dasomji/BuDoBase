import json
from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase


FIELD_NAMES = (
    "first_name",
    "last_name",
    "sex",
    "birthday",
    "stay_weeks",
    "siblings",
    "tent_request",
    "budo_experience",
    "social_security_number",
    "illness",
    "drugs",
    "vegetarian",
    "special_food",
    "swimmer",
    "consent",
    "over_the_counter_medication",
    "prescription_medication",
    "tetanus",
    "tick_vaccine",
    "organization",
    "registrant_first_name",
    "registrant_last_name",
    "registrant_email",
    "registrant_phone",
    "insured_with",
    "emergency_contacts",
    "budo_family",
)
TOP_LEVEL_KEYS = frozenset(
    {
        "request_id",
        "expected_edit_version",
        "field_baselines",
        "fields",
        "swp",
        "happy_cleaning_number",
        "expected_number_version",
        "happy_cleaning",
    }
)
BASELINE = "v1." + "A" * 43
LEGACY = "legacy:v1." + "B" * 43
BODY_LIMIT = 128 * 1024

FIELD_LABELS = {
    "first_name": "Vorname",
    "last_name": "Nachname",
    "sex": "Geschlecht",
    "birthday": "Geburtstag",
    "stay_weeks": "Aufenthaltsdauer",
    "siblings": "Geschwister",
    "tent_request": "Zeltwunsch",
    "budo_experience": "BuDo-Erfahrung",
    "social_security_number": "Sozialversicherungsnummer",
    "illness": "Krankheiten und Besonderheiten",
    "drugs": "Medikamente",
    "vegetarian": "Vegetarisch",
    "special_food": "Besondere Ernährung",
    "swimmer": "Schwimmkenntnisse",
    "consent": "Einverständniserklärung",
    "over_the_counter_medication": "Rezeptfreie Medikamente",
    "prescription_medication": "Rezeptpflichtige Medikamente",
    "tetanus": "Tetanusimpfung",
    "tick_vaccine": "Zeckenimpfung",
    "organization": "Organisation",
    "registrant_first_name": "Vorname der anmeldenden Person",
    "registrant_last_name": "Nachname der anmeldenden Person",
    "registrant_email": "E-Mail der anmeldenden Person",
    "registrant_phone": "Mobilnummer der anmeldenden Person",
    "insured_with": "Hauptversichert bei",
    "emergency_contacts": "Notfallkontakte",
    "budo_family": "BuDo-Familie",
}
FIELD_LIMITS = {
    "first_name": 255,
    "last_name": 255,
    "siblings": 255,
    "tent_request": 255,
    "social_security_number": 255,
    "illness": 10_000,
    "drugs": 10_000,
    "special_food": 255,
    "swimmer": 255,
    "over_the_counter_medication": 10_000,
    "prescription_medication": 255,
    "tetanus": 255,
    "tick_vaccine": 255,
    "organization": 255,
    "registrant_first_name": 255,
    "registrant_last_name": 255,
    "registrant_email": 255,
    "registrant_phone": 255,
    "insured_with": 255,
    "emergency_contacts": 10_000,
}


class KidEditDecoderTests(SimpleTestCase):
    @staticmethod
    def public_decoder():
        from budo_app.kid_edit_contracts import (
            KidEditParseError,
            decode_kid_edit_request,
        )

        return decode_kid_edit_request, KidEditParseError

    @staticmethod
    def valid_fields():
        return {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "sex": None,
            "birthday": None,
            "stay_weeks": None,
            "siblings": "",
            "tent_request": "",
            "budo_experience": None,
            "social_security_number": "",
            "illness": "Synthetic condition",
            "drugs": "",
            "vegetarian": None,
            "special_food": "",
            "swimmer": "gut",
            "consent": None,
            "over_the_counter_medication": "",
            "prescription_medication": "",
            "tetanus": "",
            "tick_vaccine": "",
            "organization": "",
            "registrant_first_name": "",
            "registrant_last_name": "",
            "registrant_email": "",
            "registrant_phone": "",
            "insured_with": "",
            "emergency_contacts": "",
            "budo_family": None,
        }

    @classmethod
    def valid_payload(cls):
        return {
            "request_id": "request-163-03",
            "expected_edit_version": 4,
            "field_baselines": {name: BASELINE for name in FIELD_NAMES},
            "fields": cls.valid_fields(),
            "swp": [],
            "happy_cleaning_number": None,
            "expected_number_version": 3,
            "happy_cleaning": [],
        }

    @staticmethod
    def encode(payload):
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    def decode(self, payload=None, *, raw_body=None, content_type="application/json"):
        decoder, _error_type = self.public_decoder()
        if raw_body is None:
            raw_body = self.encode(payload if payload is not None else self.valid_payload())
        return decoder(raw_body, content_type)

    def assert_parse_error(
        self,
        result,
        *,
        status,
        code,
        field,
        field_code=None,
        message=None,
    ):
        _decoder, error_type = self.public_decoder()
        self.assertIsInstance(result, error_type)
        self.assertEqual(result.status, status)
        self.assertEqual(result.code, code)
        self.assertIn(field, result.errors)
        self.assertTrue(result.errors[field])
        field_error = result.errors[field][0]
        if field_code is not None:
            self.assertEqual(field_error.code, field_code)
        self.assertIsInstance(field_error.message, str)
        self.assertTrue(field_error.message)
        if message is not None:
            self.assertEqual(field_error.message, message)
        return result

    def test_valid_request_returns_deeply_immutable_normalized_dto(self):
        payload = self.valid_payload()
        payload["request_id"] = "  request-163-03  "
        payload["fields"]["first_name"] = "  Ada  "
        payload["fields"]["illness"] = "Synthetic secret\r\nSecond line"

        with self.assertNoLogs(level="DEBUG"):
            decoded = self.decode(payload)

        self.assertEqual(decoded.request_id, "request-163-03")
        self.assertEqual(decoded.expected_edit_version, 4)
        self.assertEqual(tuple(decoded.fields), FIELD_NAMES)
        self.assertEqual(decoded.fields["first_name"], "Ada")
        self.assertEqual(
            decoded.fields["illness"],
            "Synthetic secret\nSecond line",
        )
        self.assertEqual(tuple(decoded.field_baselines), FIELD_NAMES)
        self.assertEqual(decoded.swp, ())
        self.assertEqual(decoded.happy_cleaning, ())
        self.assertIsNone(decoded.happy_cleaning_number)
        self.assertNotIn("Synthetic secret", repr(decoded))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            decoded.request_id = "changed"
        with self.assertRaises(TypeError):
            decoded.fields["first_name"] = "changed"

    def test_byte_limit_is_checked_before_utf8_and_json_decode(self):
        body = self.encode(self.valid_payload())
        exact = body + b" " * (BODY_LIMIT - len(body))
        decoded = self.decode(raw_body=exact)
        self.assertEqual(decoded.request_id, "request-163-03")

        oversized_invalid = b"{" + b"x" * (BODY_LIMIT - 1) + b"\xff"
        result = self.decode(raw_body=oversized_invalid)
        self.assert_parse_error(
            result,
            status=413,
            code="request_too_large",
            field="_form",
        )

    def test_only_exact_json_media_type_is_supported(self):
        self.assertEqual(
            self.decode(content_type="application/json").request_id,
            "request-163-03",
        )
        for content_type in (
            "",
            "text/json",
            "application/problem+json",
            "Application/JSON",
            "application/json; charset=utf-8",
        ):
            with self.subTest(content_type=content_type):
                self.assert_parse_error(
                    self.decode(content_type=content_type),
                    status=415,
                    code="unsupported_media_type",
                    field="_form",
                )

    def test_malformed_utf8_json_and_non_object_are_invalid_json(self):
        for raw_body in (
            b"\xff",
            b"{",
            b"null",
            b"[]",
            b'"text"',
            b"1",
        ):
            with self.subTest(raw_body=repr(raw_body)):
                self.assert_parse_error(
                    self.decode(raw_body=raw_body),
                    status=400,
                    code="invalid_json",
                    field="_form",
                )

    def test_top_level_keys_are_exact(self):
        self.assertEqual(frozenset(self.valid_payload()), TOP_LEVEL_KEYS)
        missing = self.valid_payload()
        del missing["swp"]
        self.assert_parse_error(
            self.decode(missing),
            status=422,
            code="validation_error",
            field="_form",
            field_code="missing_field",
            message="Die Formulardaten sind unvollständig. Bitte Seite neu laden.",
        )
        unknown = self.valid_payload()
        unknown["child_id"] = 7
        self.assert_parse_error(
            self.decode(unknown),
            status=422,
            code="validation_error",
            field="_form",
            field_code="unknown_field",
            message="Die Formulardaten enthalten unbekannte Felder. Bitte Seite neu laden.",
        )

    def test_fields_and_baselines_are_exact_27_key_objects(self):
        for container_name in ("fields", "field_baselines"):
            not_object = self.valid_payload()
            not_object[container_name] = []
            self.assert_parse_error(
                self.decode(not_object),
                status=422,
                code="validation_error",
                field="_form",
            )

            missing = self.valid_payload()
            del missing[container_name]["siblings"]
            self.assert_parse_error(
                self.decode(missing),
                status=422,
                code="validation_error",
                field="_form",
                field_code="missing_field",
            )

            unknown = self.valid_payload()
            unknown[container_name]["excluded_internal_field"] = "x"
            self.assert_parse_error(
                self.decode(unknown),
                status=422,
                code="validation_error",
                field="_form",
                field_code="unknown_field",
            )

    def test_request_id_is_trimmed_nonempty_text_at_most_255(self):
        payload = self.valid_payload()
        payload["request_id"] = "  " + "r" * 255 + "  "
        self.assertEqual(self.decode(payload).request_id, "r" * 255)

        for value, code in ((None, "invalid_type"), (1, "invalid_type"), (" ", "required"), ("r" * 256, "too_long")):
            with self.subTest(value_type=type(value).__name__, code=code):
                payload = self.valid_payload()
                payload["request_id"] = value
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field="_form",
                    field_code=code,
                )

    def test_expected_versions_are_positive_json_integers(self):
        for name in ("expected_edit_version", "expected_number_version"):
            for value in (True, False, None, 0, -1, 1.0, "1"):
                with self.subTest(field=name, value=repr(value)):
                    payload = self.valid_payload()
                    payload[name] = value
                    self.assert_parse_error(
                        self.decode(payload),
                        status=422,
                        code="validation_error",
                        field="_form",
                        field_code="invalid_type",
                    )

    def test_field_baselines_receive_syntax_checks_only(self):
        payload = self.valid_payload()
        payload["field_baselines"]["illness"] = "v1." + "Z" * 43
        self.assertEqual(
            self.decode(payload).field_baselines["illness"],
            "v1." + "Z" * 43,
        )
        for token in (None, BASELINE[:-1], BASELINE + "A", "v2." + "A" * 43, LEGACY):
            with self.subTest(token=repr(token)):
                payload = self.valid_payload()
                payload["field_baselines"]["illness"] = token
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field="illness",
                    field_code="invalid_type",
                )

    def test_field_values_reuse_contract_normalization_and_validation(self):
        payload = self.valid_payload()
        payload["fields"].update(
            {
                "first_name": "\u2003Ada\u2002",
                "birthday": "2012-02-29",
                "vegetarian": False,
                "registrant_email": " ada@ ",
            }
        )
        decoded = self.decode(payload)
        self.assertEqual(decoded.fields["first_name"], "Ada")
        self.assertEqual(decoded.fields["birthday"], "2012-02-29")
        self.assertIs(decoded.fields["vegetarian"], False)
        self.assertEqual(decoded.fields["registrant_email"], "ada@")

        invalid_cases = (
            ("first_name", " ", "required", "Vorname ist erforderlich."),
            ("siblings", None, "invalid_type", None),
            ("birthday", "2012-02-30", "invalid_date", "Geburtstag muss ein gültiges Datum sein."),
            ("sex", "weiblich", "invalid_choice", "Bitte eine gültige Auswahl treffen."),
            ("illness", "x" * 10_001, "too_long", None),
        )
        for name, value, code, message in invalid_cases:
            with self.subTest(field=name, code=code):
                payload = self.valid_payload()
                payload["fields"][name] = value
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=name,
                    field_code=code,
                    message=message,
                )

    def test_controlled_legacy_tokens_are_deferred_without_verification(self):
        payload = self.valid_payload()
        for name in ("sex", "stay_weeks", "vegetarian", "budo_family"):
            payload["fields"][name] = LEGACY
        decoded = self.decode(payload)
        for name in ("sex", "stay_weeks", "vegetarian", "budo_family"):
            self.assertEqual(decoded.fields[name], LEGACY)

        payload = self.valid_payload()
        payload["fields"]["sex"] = LEGACY[:-1]
        self.assert_parse_error(
            self.decode(payload),
            status=422,
            code="validation_error",
            field="sex",
            field_code="invalid_choice",
        )

    def test_ordinary_legacy_prefixed_text_is_not_a_reserved_token(self):
        payload = self.valid_payload()
        payload["fields"]["illness"] = "legacy: condition"
        self.assertEqual(
            self.decode(payload).fields["illness"],
            "legacy: condition",
        )

        payload["fields"]["illness"] = LEGACY
        self.assert_parse_error(
            self.decode(payload),
            status=422,
            code="validation_error",
            field="illness",
            field_code="invalid_type",
            message="Krankheiten und Besonderheiten hat ein ungültiges Format.",
        )

    def test_swp_preserve_legacy_target_has_exact_shape_and_token_syntax(self):
        preserve_token = "v1." + "C" * 43
        payload = self.valid_payload()
        payload["swp"] = [
            {
                "period_id": 17,
                "baseline": BASELINE,
                "target": {
                    "kind": "preserve_legacy",
                    "token": preserve_token,
                },
            }
        ]
        decoded = self.decode(payload)
        self.assertEqual(decoded.swp[0].target.kind, "preserve_legacy")
        self.assertEqual(decoded.swp[0].target.token, preserve_token)

        for target, code in (
            ({"kind": "preserve_legacy"}, "missing_field"),
            ({"kind": "preserve_legacy", "token": preserve_token, "focus_id": 9}, "unknown_field"),
            ({"kind": "preserve_legacy", "token": preserve_token[:-1]}, "invalid_choice"),
            ({"kind": "preserve_legacy", "token": LEGACY}, "invalid_choice"),
        ):
            with self.subTest(target=target, code=code):
                payload = self.valid_payload()
                payload["swp"] = [
                    {
                        "period_id": 17,
                        "baseline": BASELINE,
                        "target": target,
                    }
                ]
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field="swp.17",
                    field_code=code,
                )

    def test_swp_items_targets_ids_baselines_and_duplicates_are_exact(self):
        payload = self.valid_payload()
        payload["swp"] = [
            {"period_id": 17, "baseline": BASELINE, "target": {"kind": "unassigned"}},
            {"period_id": 19, "baseline": BASELINE, "target": {"kind": "focus", "focus_id": 91}},
        ]
        decoded = self.decode(payload)
        self.assertEqual(tuple(item.period_id for item in decoded.swp), (17, 19))
        self.assertEqual(decoded.swp[1].target.kind, "focus")
        self.assertEqual(decoded.swp[1].target.focus_id, 91)

        invalid_items = (
            ("not-array", "_form", None),
            ([{"period_id": 17, "baseline": BASELINE, "target": {"kind": "focus"}}], "swp.17", "missing_field"),
            ([{"period_id": 17, "baseline": BASELINE, "target": {"kind": "focus", "focus_id": 91, "extra": 1}}], "swp.17", "unknown_field"),
            ([{"period_id": True, "baseline": BASELINE, "target": {"kind": "unassigned"}}], "_form", "invalid_type"),
            ([{"period_id": 17, "baseline": "bad", "target": {"kind": "unassigned"}}], "swp.17", "invalid_type"),
            ([{"period_id": 17, "baseline": BASELINE, "target": {"kind": "other"}}], "swp.17", "invalid_choice"),
            ([{"period_id": 17, "baseline": BASELINE, "target": {"kind": "focus", "focus_id": 0}}], "swp.17", "invalid_type"),
            ([{"period_id": 17, "baseline": BASELINE, "target": {"kind": "unassigned"}}, {"period_id": 17, "baseline": BASELINE, "target": {"kind": "unassigned"}}], "swp.17", "duplicate_id"),
        )
        for value, field, field_code in invalid_items:
            with self.subTest(field=field, field_code=field_code):
                payload = self.valid_payload()
                payload["swp"] = value
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=field,
                    field_code=field_code,
                )

    def test_happy_cleaning_items_targets_versions_and_duplicates_are_exact(self):
        payload = self.valid_payload()
        payload["happy_cleaning"] = [
            {"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "unassigned"}},
            {"event_id": 43, "expected_assignment_version": 7, "target": {"kind": "excused"}},
            {"event_id": 44, "expected_assignment_version": 3, "target": {"kind": "station", "station_id": 8}},
        ]
        decoded = self.decode(payload)
        self.assertEqual(tuple(item.event_id for item in decoded.happy_cleaning), (42, 43, 44))
        self.assertEqual(decoded.happy_cleaning[2].target.kind, "station")
        self.assertEqual(decoded.happy_cleaning[2].target.station_id, 8)

        invalid_items = (
            ({}, "_form", None),
            ([{"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "station"}}], "happy_cleaning.42", "missing_field"),
            ([{"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "excused", "station_id": 8}}], "happy_cleaning.42", "unknown_field"),
            ([{"event_id": 42, "expected_assignment_version": True, "target": {"kind": "unassigned"}}], "happy_cleaning.42", "invalid_type"),
            ([{"event_id": 42, "expected_assignment_version": -1, "target": {"kind": "unassigned"}}], "happy_cleaning.42", "invalid_type"),
            ([{"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "other"}}], "happy_cleaning.42", "invalid_choice"),
            ([{"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "unassigned"}}, {"event_id": 42, "expected_assignment_version": 0, "target": {"kind": "unassigned"}}], "happy_cleaning.42", "duplicate_id"),
        )
        for value, field, field_code in invalid_items:
            with self.subTest(field=field, field_code=field_code):
                payload = self.valid_payload()
                payload["happy_cleaning"] = value
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=field,
                    field_code=field_code,
                )

    def test_dynamic_arrays_sort_by_id_and_object_key_order_is_irrelevant(self):
        payload = self.valid_payload()
        payload["swp"] = [
            {"target": {"focus_id": 9, "kind": "focus"}, "baseline": BASELINE, "period_id": 20},
            {"baseline": BASELINE, "period_id": 10, "target": {"kind": "unassigned"}},
        ]
        payload["happy_cleaning"] = [
            {"target": {"station_id": 8, "kind": "station"}, "expected_assignment_version": 2, "event_id": 50},
            {"event_id": 40, "target": {"kind": "excused"}, "expected_assignment_version": 0},
        ]
        decoded = self.decode(payload)
        self.assertEqual(tuple(item.period_id for item in decoded.swp), (10, 20))
        self.assertEqual(tuple(item.event_id for item in decoded.happy_cleaning), (40, 50))

    def test_happy_cleaning_number_is_null_or_positive_32_bit_integer(self):
        for value in (None, 1, 2_147_483_647):
            with self.subTest(valid=value):
                payload = self.valid_payload()
                payload["happy_cleaning_number"] = value
                self.assertEqual(self.decode(payload).happy_cleaning_number, value)
        for value in (True, False, 0, -1, 1.0, "1", 2_147_483_648):
            with self.subTest(invalid=repr(value)):
                payload = self.valid_payload()
                payload["happy_cleaning_number"] = value
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field="happy_cleaning_number",
                    field_code="invalid_number",
                )

    def test_parse_errors_are_immutable_and_do_not_repr_or_log_values(self):
        payload = self.valid_payload()
        secret = "SYNTHETIC-SECRET-NOT-FOR-ERRORS"
        payload["fields"]["first_name"] = secret + "\x00"
        with self.assertNoLogs(level="DEBUG"):
            error = self.decode(payload)
        self.assert_parse_error(
            error,
            status=422,
            code="validation_error",
            field="first_name",
            field_code="invalid_type",
            message="Vorname hat ein ungültiges Format.",
        )
        self.assertNotIn(secret, repr(error))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            error.status = 200
        with self.assertRaises(TypeError):
            error.errors["first_name"] = ()

    def test_independent_field_errors_are_returned_together(self):
        payload = self.valid_payload()
        payload["fields"]["first_name"] = " "
        payload["fields"]["birthday"] = "2012-02-30"
        error = self.decode(payload)
        self.assert_parse_error(
            error,
            status=422,
            code="validation_error",
            field="first_name",
            field_code="required",
        )
        self.assertEqual(error.errors["birthday"][0].code, "invalid_date")

    def test_internal_text_codes_are_mapped_to_public_invalid_type(self):
        for name, value in (
            ("first_name", "Ada\nLovelace"),
            ("first_name", "Ada\tLovelace"),
            ("illness", "condition\x00"),
        ):
            with self.subTest(field=name, value=repr(value)):
                payload = self.valid_payload()
                payload["fields"][name] = value
                error = self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=name,
                    field_code="invalid_type",
                    message=(
                        f"{FIELD_LABELS[name]} hat ein ungültiges Format."
                    ),
                )
                public_codes = {
                    item.code
                    for errors in error.errors.values()
                    for item in errors
                }
                self.assertNotIn("control", public_codes)
                self.assertNotIn("single_line", public_codes)

    def test_every_field_has_exact_label_specific_type_message(self):
        for name in FIELD_NAMES:
            with self.subTest(field=name):
                payload = self.valid_payload()
                payload["fields"][name] = []
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=name,
                    field_code="invalid_type",
                    message=(
                        f"{FIELD_LABELS[name]} hat ein ungültiges Format."
                    ),
                )

    def test_every_bounded_field_has_exact_label_specific_length_message(self):
        for name, limit in FIELD_LIMITS.items():
            with self.subTest(field=name, limit=limit):
                payload = self.valid_payload()
                payload["fields"][name] = "x" * (limit + 1)
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=name,
                    field_code="too_long",
                    message=(
                        f"{FIELD_LABELS[name]} darf höchstens {limit} "
                        "Zeichen lang sein."
                    ),
                )

    def test_generic_public_codes_have_exact_german_messages(self):
        cases = []

        payload = self.valid_payload()
        payload["happy_cleaning_number"] = 0
        cases.append(
            (
                payload,
                "happy_cleaning_number",
                "invalid_number",
                "Happy-Cleaning-Nummer muss eine positive ganze Zahl sein.",
            )
        )

        payload = self.valid_payload()
        payload["swp"] = [
            {"period_id": 17, "baseline": BASELINE, "target": {"kind": "unassigned"}},
            {"period_id": 17, "baseline": BASELINE, "target": {"kind": "unassigned"}},
        ]
        cases.append(
            (
                payload,
                "swp.17",
                "duplicate_id",
                "Diese Auswahl wurde mehrfach übermittelt. Bitte Seite neu laden.",
            )
        )

        payload = self.valid_payload()
        payload["swp"] = [
            {"period_id": 17, "baseline": BASELINE, "target": {"kind": "focus"}}
        ]
        cases.append(
            (
                payload,
                "swp.17",
                "missing_field",
                "Die Formulardaten sind unvollständig. Bitte Seite neu laden.",
            )
        )

        payload = self.valid_payload()
        payload["happy_cleaning"] = [
            {
                "event_id": 42,
                "expected_assignment_version": 0,
                "target": {"kind": "excused", "station_id": 8},
            }
        ]
        cases.append(
            (
                payload,
                "happy_cleaning.42",
                "unknown_field",
                "Die Formulardaten enthalten unbekannte Felder. Bitte Seite neu laden.",
            )
        )

        for payload, field, code, message in cases:
            with self.subTest(field=field, code=code):
                self.assert_parse_error(
                    self.decode(payload),
                    status=422,
                    code="validation_error",
                    field=field,
                    field_code=code,
                    message=message,
                )

    def test_transport_and_request_structure_errors_use_form_key(self):
        cases = (
            (self.decode(raw_body=b"{"), 400, "invalid_json", "Die Anfrage enthält kein gültiges JSON."),
            (self.decode(content_type="text/plain"), 415, "unsupported_media_type", "Bitte JSON-Daten senden."),
            (self.decode(raw_body=b"x" * (BODY_LIMIT + 1)), 413, "request_too_large", "Die Anfrage ist zu groß."),
        )
        for error, status, code, message in cases:
            with self.subTest(code=code):
                self.assert_parse_error(
                    error,
                    status=status,
                    code=code,
                    field="_form",
                    field_code=code,
                    message=message,
                )

        for name, value in (
            ("request_id", " "),
            ("expected_edit_version", 0),
            ("expected_number_version", True),
        ):
            with self.subTest(field=name):
                payload = self.valid_payload()
                payload[name] = value
                error = self.decode(payload)
                self.assertEqual(tuple(error.errors), ("_form",))

    def test_mixed_parse_failures_aggregate_in_canonical_form_order(self):
        payload = self.valid_payload()
        payload["fields"]["first_name"] = " "
        payload["fields"]["birthday"] = "2012-02-30"
        payload["swp"] = [
            {
                "period_id": 17,
                "baseline": BASELINE,
                "target": {"kind": "focus", "focus_id": 0},
            }
        ]
        payload["happy_cleaning_number"] = 0
        payload["happy_cleaning"] = [
            {
                "event_id": 42,
                "expected_assignment_version": -1,
                "target": {"kind": "unassigned"},
            }
        ]
        error = self.decode(payload)
        self.assertEqual(
            tuple(error.errors),
            (
                "first_name",
                "birthday",
                "swp.17",
                "happy_cleaning_number",
                "happy_cleaning.42",
            ),
        )

    def test_all_inner_sections_aggregate_every_independent_error_in_order(self):
        payload = self.valid_payload()
        payload["request_id"] = " "
        payload["expected_edit_version"] = False
        payload["expected_number_version"] = 0
        payload["field_baselines"]["illness"] = "bad-illness-token"
        payload["field_baselines"]["last_name"] = "bad-name-token"
        payload["swp"] = [
            {
                "period_id": 20,
                "baseline": BASELINE,
                "target": {"kind": "focus", "focus_id": 0},
            },
            {
                "period_id": 10,
                "baseline": "bad-swp-token",
                "target": {"kind": "unassigned"},
            },
        ]
        payload["happy_cleaning_number"] = 0
        payload["happy_cleaning"] = [
            {
                "event_id": 50,
                "expected_assignment_version": -1,
                "target": {"kind": "unassigned"},
            },
            {
                "event_id": 40,
                "expected_assignment_version": 0,
                "target": {"kind": "station", "station_id": 0},
            },
        ]

        error = self.decode(payload)
        self.assertEqual(
            tuple(error.errors),
            (
                "_form",
                "last_name",
                "illness",
                "swp.10",
                "swp.20",
                "happy_cleaning_number",
                "happy_cleaning.40",
                "happy_cleaning.50",
            ),
        )
        self.assertEqual(
            tuple(item.code for item in error.errors["_form"]),
            ("required", "invalid_type", "invalid_type"),
        )
        self.assertEqual(
            tuple(
                error.errors[key][0].code
                for key in tuple(error.errors)[1:]
            ),
            (
                "invalid_type",
                "invalid_type",
                "invalid_type",
                "invalid_type",
                "invalid_number",
                "invalid_type",
                "invalid_type",
            ),
        )

    def test_nested_dto_reprs_redact_every_baseline_and_preserve_token(self):
        preserve_token = "v1." + "C" * 43
        payload = self.valid_payload()
        payload["fields"]["sex"] = LEGACY
        payload["swp"] = [
            {
                "period_id": 17,
                "baseline": BASELINE,
                "target": {
                    "kind": "preserve_legacy",
                    "token": preserve_token,
                },
            }
        ]
        decoded = self.decode(payload)

        for dto in (decoded, decoded.swp[0], decoded.swp[0].target):
            with self.subTest(dto_type=type(dto).__name__):
                rendered = repr(dto)
                self.assertNotIn(BASELINE, rendered)
                self.assertNotIn(preserve_token, rendered)
                self.assertNotIn(LEGACY, rendered)
