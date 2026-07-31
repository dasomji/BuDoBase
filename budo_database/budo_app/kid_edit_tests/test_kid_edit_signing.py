import inspect
import re

from django.test import SimpleTestCase, override_settings


FIELD_TOKEN = re.compile(r"\Av1\.[A-Za-z0-9_-]{43}\Z")
LEGACY_TOKEN = re.compile(r"\Alegacy:v1\.[A-Za-z0-9_-]{43}\Z")


class EqualityTrap(str):
    def __eq__(self, other):
        raise AssertionError("verification used ordinary equality")

    def __ne__(self, other):
        raise AssertionError("verification used ordinary inequality")


@override_settings(
    SECRET_KEY="synthetic-kid-edit-primary-key",
    SECRET_KEY_FALLBACKS=[],
)
class KidEditSigningTests(SimpleTestCase):
    @staticmethod
    def public_signing():
        from budo_app.kid_edit_contracts import (
            sign_field_baseline,
            sign_legacy_preserve_value,
            sign_swp_baseline,
            verify_field_baseline,
            verify_legacy_preserve_value,
            verify_swp_baseline,
        )

        return (
            sign_field_baseline,
            verify_field_baseline,
            sign_swp_baseline,
            verify_swp_baseline,
            sign_legacy_preserve_value,
            verify_legacy_preserve_value,
        )

    @staticmethod
    def field_context(**overrides):
        context = {
            "turnus_id": 161,
            "child_id": 7,
            "field_name": "illness",
            "canonical_value": "Synthetic baseline value",
        }
        context.update(overrides)
        return context

    @staticmethod
    def swp_context(**overrides):
        context = {
            "turnus_id": 161,
            "child_id": 7,
            "period_id": 17,
            "current_focus_ids": (3, 9),
        }
        context.update(overrides)
        return context

    @staticmethod
    def legacy_context(**overrides):
        context = {
            "turnus_id": 161,
            "child_id": 7,
            "field_name": "sex",
            "raw_storage_value": "Synthetic legacy choice",
        }
        context.update(overrides)
        return context

    def test_public_seams_do_not_accept_or_bind_edit_version(self):
        for callable_ in self.public_signing():
            with self.subTest(callable=callable_.__name__):
                self.assertNotIn(
                    "edit_version",
                    inspect.signature(callable_).parameters,
                )

    def test_field_baseline_is_deterministic_opaque_and_fixed_width(self):
        sign, verify, *_rest = self.public_signing()
        context = self.field_context()

        with self.assertNoLogs(level="DEBUG"):
            first = sign(**context)
            second = sign(**context)
            verified = verify(first, **context)

        self.assertEqual(first, second)
        self.assertRegex(first, FIELD_TOKEN)
        self.assertEqual(len(first), 46)
        self.assertNotIn(context["canonical_value"], first)
        self.assertIs(verified, True)
        self.assertNotIn(context["canonical_value"], repr(verified))

    def test_field_baseline_binds_every_context_component_and_value(self):
        sign, verify, *_rest = self.public_signing()
        context = self.field_context()
        token = sign(**context)

        for changed in (
            self.field_context(turnus_id=162),
            self.field_context(child_id=8),
            self.field_context(field_name="drugs"),
            self.field_context(canonical_value="Different value"),
        ):
            with self.subTest(changed=changed):
                self.assertIs(verify(token, **changed), False)

        self.assertIs(
            verify(token, **self.field_context(field_name="unknown_field")),
            False,
        )
        with self.assertRaises(ValueError):
            sign(**self.field_context(field_name="unknown_field"))

    def test_field_value_encoding_distinguishes_bool_int_null_and_text(self):
        sign, verify, *_rest = self.public_signing()
        values = (None, "", False, 0, True, 1, "0", "1")
        tokens = {
            value_key: sign(
                **self.field_context(
                    field_name="budo_experience",
                    canonical_value=value,
                )
            )
            for value_key, value in (
                ("none", None),
                ("empty", ""),
                ("false", False),
                ("zero", 0),
                ("true", True),
                ("one", 1),
                ("zero_text", "0"),
                ("one_text", "1"),
            )
        }

        self.assertEqual(len(set(tokens.values())), len(values))
        false_token = tokens["false"]
        self.assertIs(
            verify(
                false_token,
                **self.field_context(
                    field_name="budo_experience",
                    canonical_value=False,
                ),
            ),
            True,
        )
        self.assertIs(
            verify(
                false_token,
                **self.field_context(
                    field_name="budo_experience",
                    canonical_value=0,
                ),
            ),
            False,
        )

    def test_swp_baseline_binds_period_and_exact_canonical_focus_set(self):
        _sign_field, _verify_field, sign, verify, *_rest = self.public_signing()
        context = self.swp_context()
        token = sign(**context)

        self.assertRegex(token, FIELD_TOKEN)
        self.assertEqual(token, sign(**context))
        self.assertIs(verify(token, **context), True)
        for changed in (
            self.swp_context(turnus_id=162),
            self.swp_context(child_id=8),
            self.swp_context(period_id=18),
            self.swp_context(current_focus_ids=()),
            self.swp_context(current_focus_ids=(3,)),
            self.swp_context(current_focus_ids=(3, 10)),
            self.swp_context(current_focus_ids=(9, 3)),
            self.swp_context(current_focus_ids=(3, 3)),
        ):
            with self.subTest(changed=changed):
                self.assertIs(verify(token, **changed), False)

    def test_swp_signing_requires_sorted_unique_positive_integer_ids(self):
        _sign_field, _verify_field, sign, _verify, *_rest = self.public_signing()
        for invalid_ids in ((9, 3), (3, 3), (True,), (0,), (-1,), [3, 9]):
            with self.subTest(current_focus_ids=invalid_ids):
                with self.assertRaises((TypeError, ValueError)):
                    sign(**self.swp_context(current_focus_ids=invalid_ids))
        for invalid_period_id in (True, 0, -1, "17"):
            with self.subTest(period_id=invalid_period_id):
                with self.assertRaises((TypeError, ValueError)):
                    sign(**self.swp_context(period_id=invalid_period_id))

    def test_legacy_preserve_value_is_opaque_and_authenticates_exact_raw(self):
        *_, sign, verify = self.public_signing()
        context = self.legacy_context()

        with self.assertNoLogs(level="DEBUG"):
            token = sign(**context)
            verified = verify(token, **context)

        self.assertRegex(token, LEGACY_TOKEN)
        self.assertEqual(len(token), 53)
        self.assertNotIn(context["raw_storage_value"], token)
        self.assertIs(verified, True)
        for changed in (
            self.legacy_context(turnus_id=162),
            self.legacy_context(child_id=8),
            self.legacy_context(field_name="vegetarian"),
            self.legacy_context(raw_storage_value="synthetic legacy choice"),
            self.legacy_context(raw_storage_value=" Synthetic legacy choice "),
        ):
            with self.subTest(changed=changed):
                self.assertIs(verify(token, **changed), False)

    def test_legacy_raw_encoding_distinguishes_bool_and_integer(self):
        *_, sign, verify = self.public_signing()
        false_context = self.legacy_context(
            field_name="stay_weeks",
            raw_storage_value=False,
        )
        zero_context = self.legacy_context(
            field_name="stay_weeks",
            raw_storage_value=0,
        )
        false_token = sign(**false_context)
        zero_token = sign(**zero_context)

        self.assertNotEqual(false_token, zero_token)
        self.assertIs(verify(false_token, **false_context), True)
        self.assertIs(verify(false_token, **zero_context), False)

    def test_primary_and_fallback_keys_support_rotation(self):
        sign, verify, sign_swp, verify_swp, sign_legacy, verify_legacy = (
            self.public_signing()
        )
        with self.settings(
            SECRET_KEY="synthetic-old-key",
            SECRET_KEY_FALLBACKS=[],
        ):
            old_field = sign(**self.field_context())
            old_swp = sign_swp(**self.swp_context())
            old_legacy = sign_legacy(**self.legacy_context())

        with self.settings(
            SECRET_KEY="synthetic-current-key",
            SECRET_KEY_FALLBACKS=["synthetic-old-key"],
        ):
            self.assertIs(verify(old_field, **self.field_context()), True)
            self.assertIs(verify_swp(old_swp, **self.swp_context()), True)
            self.assertIs(
                verify_legacy(old_legacy, **self.legacy_context()),
                True,
            )
            self.assertNotEqual(sign(**self.field_context()), old_field)

        with self.settings(
            SECRET_KEY="synthetic-current-key",
            SECRET_KEY_FALLBACKS=[],
        ):
            self.assertIs(verify(old_field, **self.field_context()), False)
            self.assertIs(verify_swp(old_swp, **self.swp_context()), False)
            self.assertIs(
                verify_legacy(old_legacy, **self.legacy_context()),
                False,
            )

    def test_unknown_key_is_rejected(self):
        sign, verify, *_rest = self.public_signing()
        with self.settings(
            SECRET_KEY="synthetic-unknown-key",
            SECRET_KEY_FALLBACKS=[],
        ):
            token = sign(**self.field_context())

        self.assertIs(verify(token, **self.field_context()), False)

    def test_field_and_swp_tokens_cannot_cross_verifier_kinds(self):
        sign_field, verify_field, sign_swp, verify_swp, *_rest = (
            self.public_signing()
        )
        field_token = sign_field(**self.field_context())
        swp_token = sign_swp(**self.swp_context())

        self.assertIs(
            verify_swp(field_token, **self.swp_context()),
            False,
        )
        self.assertIs(
            verify_field(swp_token, **self.field_context()),
            False,
        )

    def test_verification_does_not_use_ordinary_token_equality(self):
        sign, verify, *_rest = self.public_signing()
        token = sign(**self.field_context())
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        self.assertIs(
            verify(EqualityTrap(token), **self.field_context()),
            True,
        )
        self.assertIs(
            verify(EqualityTrap(tampered), **self.field_context()),
            False,
        )

    def test_malformed_wrong_version_and_wrong_token_kind_are_neutral(self):
        sign, verify, sign_swp, verify_swp, sign_legacy, verify_legacy = (
            self.public_signing()
        )
        field = sign(**self.field_context())
        swp = sign_swp(**self.swp_context())
        legacy = sign_legacy(**self.legacy_context())
        malformed = (
            None,
            1,
            "",
            "v1.",
            "v1." + "a" * 42,
            "v1." + "a" * 44,
            "v1." + "!" * 43,
            "v1." + "a" * 42 + "=",
            "v2." + field.removeprefix("v1."),
            "legacy:" + field,
            "legacy:v2." + legacy.removeprefix("legacy:v1."),
            "x" * 10_000,
        )
        for token in malformed:
            with self.subTest(
                token_type=type(token).__name__,
                token=repr(token)[:80],
            ):
                self.assertIs(
                    verify(token, **self.field_context()),
                    False,
                )
                self.assertIs(
                    verify_swp(token, **self.swp_context()),
                    False,
                )
                self.assertIs(
                    verify_legacy(token, **self.legacy_context()),
                    False,
                )

        self.assertIs(verify(field, **self.field_context()), True)
        self.assertIs(verify_swp(swp, **self.swp_context()), True)
        self.assertIs(verify_legacy(legacy, **self.legacy_context()), True)
        self.assertIs(verify(legacy, **self.field_context()), False)
        self.assertIs(verify_legacy(field, **self.legacy_context()), False)
