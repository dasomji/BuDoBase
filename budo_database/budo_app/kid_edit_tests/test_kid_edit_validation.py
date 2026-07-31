import json
from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase, override_settings

from budo_app.kid_edit_tests.test_kid_edit_decoder import (
    BASELINE,
    FIELD_LABELS,
    FIELD_NAMES,
    LEGACY,
    KidEditDecoderTests,
)


RAW_FIELDS = {
    "kid_vorname": "Ada",
    "kid_nachname": "Lovelace",
    "sex": None,
    "kid_birthday": None,
    "turnus_dauer": None,
    "geschwister": None,
    "zeltwunsch": None,
    "budo_erfahrung": None,
    "sozialversicherungsnr": None,
    "illness": "Synthetic condition",
    "drugs": None,
    "vegetarisch": None,
    "special_food_description": None,
    "swimmer": "gut",
    "einverstaendnis_erklaerung": None,
    "rezeptfreie_medikamente": None,
    "rezept_medikamente": None,
    "tetanusimpfung": None,
    "zeckenimpfung": None,
    "anmelde_organisation": None,
    "anmelder_vorname": "",
    "anmelder_nachname": "",
    "anmelder_email": None,
    "anmelder_mobil": None,
    "hauptversichert_bei": None,
    "notfall_kontakte": None,
    "budo_family": None,
}


@override_settings(
    SECRET_KEY="synthetic-kid-edit-context-key",
    SECRET_KEY_FALLBACKS=[],
)
class KidEditValidationTests(SimpleTestCase):
    @staticmethod
    def public_context():
        from budo_app.kid_edit_contracts import (
            KidEditCurrentHappyCleaningEvent,
            KidEditCurrentHappyCleaningTarget,
            KidEditCurrentState,
            KidEditCurrentSwpPeriod,
            KidEditValidationError,
            validate_kid_edit_command,
        )

        return (
            KidEditCurrentState,
            KidEditCurrentSwpPeriod,
            KidEditCurrentHappyCleaningEvent,
            KidEditCurrentHappyCleaningTarget,
            KidEditValidationError,
            validate_kid_edit_command,
        )

    @staticmethod
    def contract_api():
        from budo_app.kid_edit_contracts import (
            FIELD_CONTRACTS,
            canonicalize_storage_value,
            decode_kid_edit_request,
            sign_field_baseline,
            sign_legacy_preserve_value,
            sign_swp_baseline,
        )

        return (
            FIELD_CONTRACTS,
            canonicalize_storage_value,
            decode_kid_edit_request,
            sign_field_baseline,
            sign_legacy_preserve_value,
            sign_swp_baseline,
        )

    @classmethod
    def current_state(cls, **overrides):
        (
            state_type,
            period_type,
            event_type,
            target_type,
            _error_type,
            _validate,
        ) = cls.public_context()
        values = {
            "turnus_id": 161,
            "child_id": 7,
            "edit_version": 4,
            "number_version": 3,
            "happy_cleaning_number": 42,
            "raw_fields": dict(RAW_FIELDS),
            "periods": (
                period_type(
                    period_id=17,
                    available_focus_ids=(91, 92),
                    current_focus_ids=(91,),
                ),
                period_type(
                    period_id=18,
                    available_focus_ids=(101,),
                    current_focus_ids=(),
                ),
            ),
            "events": (
                event_type(
                    event_id=42,
                    available_station_ids=(8, 9),
                    current_assignment_version=11,
                    current_target=target_type(kind="station", station_id=8),
                ),
                event_type(
                    event_id=43,
                    available_station_ids=(10,),
                    current_assignment_version=0,
                    current_target=target_type(kind="unassigned"),
                ),
            ),
        }
        values.update(overrides)
        return state_type(**values)

    @classmethod
    def payload_for(cls, current):
        (
            contracts,
            read,
            _decode,
            sign_field,
            _sign_legacy,
            sign_swp,
        ) = cls.contract_api()
        payload = KidEditDecoderTests.valid_payload()
        payload["expected_edit_version"] = current.edit_version
        payload["expected_number_version"] = current.number_version
        payload["happy_cleaning_number"] = current.happy_cleaning_number
        payload["field_baselines"] = {}
        payload["fields"] = {}
        for field in contracts:
            raw = current.raw_fields[field.storage_name]
            canonical = read(field, raw).api_value
            payload["field_baselines"][field.api_name] = sign_field(
                turnus_id=current.turnus_id,
                child_id=current.child_id,
                field_name=field.api_name,
                canonical_value=canonical,
            )
            payload["fields"][field.api_name] = canonical
        payload["swp"] = []
        for period in current.periods:
            baseline = sign_swp(
                turnus_id=current.turnus_id,
                child_id=current.child_id,
                period_id=period.period_id,
                current_focus_ids=period.current_focus_ids,
            )
            if len(period.current_focus_ids) > 1:
                target = {"kind": "preserve_legacy", "token": baseline}
            elif period.current_focus_ids:
                target = {
                    "kind": "focus",
                    "focus_id": period.current_focus_ids[0],
                }
            else:
                target = {"kind": "unassigned"}
            payload["swp"].append(
                {
                    "period_id": period.period_id,
                    "baseline": baseline,
                    "target": target,
                }
            )
        payload["happy_cleaning"] = []
        for event in current.events:
            target = {"kind": event.current_target.kind}
            if event.current_target.kind == "station":
                target["station_id"] = event.current_target.station_id
            payload["happy_cleaning"].append(
                {
                    "event_id": event.event_id,
                    "expected_assignment_version": (
                        event.current_assignment_version
                    ),
                    "target": target,
                }
            )
        return payload

    @classmethod
    def decode(cls, payload):
        _contracts, _read, decoder, *_rest = cls.contract_api()
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return decoder(raw, "application/json")

    @classmethod
    def validate(cls, payload, current):
        *_types, validate = cls.public_context()
        return validate(cls.decode(payload), current)

    def assert_validation_error(
        self,
        result,
        *,
        status,
        code,
        keys,
    ):
        *_types, error_type, _validate = self.public_context()
        self.assertIsInstance(result, error_type)
        self.assertEqual(result.status, status)
        self.assertEqual(result.code, code)
        self.assertEqual(tuple(result.errors), tuple(keys))
        return result

    def test_current_snapshot_and_validated_command_are_deeply_immutable(self):
        current = self.current_state()
        self.assertEqual(tuple(current.raw_fields), tuple(RAW_FIELDS))
        self.assertEqual(tuple(item.period_id for item in current.periods), (17, 18))
        self.assertEqual(tuple(item.event_id for item in current.events), (42, 43))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            current.edit_version = 5
        with self.assertRaises(TypeError):
            current.raw_fields["kid_vorname"] = "Changed"

        validated = self.validate(self.payload_for(current), current)
        self.assertEqual(validated.turnus_id, 161)
        self.assertEqual(validated.child_id, 7)
        self.assertEqual(validated.storage_fields["kid_vorname"], "Ada")
        self.assertEqual(tuple(item.period_id for item in validated.swp), (17, 18))
        self.assertEqual(tuple(item.event_id for item in validated.happy_cleaning), (42, 43))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            validated.child_id = 8
        with self.assertRaises(TypeError):
            validated.storage_fields["kid_vorname"] = "Changed"

    def test_exact_period_and_event_sets_include_zero_configuration(self):
        current = self.current_state(periods=(), events=())
        payload = self.payload_for(current)
        validated = self.validate(payload, current)
        self.assertEqual(validated.swp, ())
        self.assertEqual(validated.happy_cleaning, ())

        for collection, item in (
            ("swp", {"period_id": 99, "baseline": BASELINE, "target": {"kind": "unassigned"}}),
            ("happy_cleaning", {"event_id": 99, "expected_assignment_version": 0, "target": {"kind": "unassigned"}}),
        ):
            with self.subTest(collection=collection):
                changed = self.payload_for(current)
                changed[collection] = [item]
                error = self.assert_validation_error(
                    self.validate(changed, current),
                    status=409,
                    code="conflict",
                    keys=("_form",),
                )
                self.assertEqual(
                    error.errors["_form"][0].code,
                    "configuration_changed",
                )
                self.assertEqual(
                    error.errors["_form"][0].message,
                    "Die Einteilungen wurden zwischenzeitlich geändert. Bitte Seite neu laden.",
                )

    def test_unavailable_focus_and_station_are_indistinguishable(self):
        current = self.current_state()
        cases = (
            ("swp", 17, "focus_id", 999, "swp.17"),
            ("swp", 17, "focus_id", 1000, "swp.17"),
            ("happy_cleaning", 43, "station_id", 999, "happy_cleaning.43"),
            ("happy_cleaning", 43, "station_id", 1000, "happy_cleaning.43"),
        )
        observed = []
        for collection, owner_id, id_key, target_id, error_key in cases:
            payload = self.payload_for(current)
            id_name = "period_id" if collection == "swp" else "event_id"
            item = next(row for row in payload[collection] if row[id_name] == owner_id)
            item["target"] = {
                "kind": "focus" if collection == "swp" else "station",
                id_key: target_id,
            }
            error = self.assert_validation_error(
                self.validate(payload, current),
                status=422,
                code="validation_error",
                keys=(error_key,),
            )
            observed.append(error.errors[error_key][0])
        self.assertTrue(all(item.code == "unavailable" for item in observed))
        self.assertEqual(
            {item.message for item in observed},
            {"Diese Auswahl ist nicht mehr verfügbar. Bitte Seite neu laden."},
        )
        self.assertNotIn("999", repr(observed))
        self.assertNotIn("1000", repr(observed))

    def test_field_and_swp_baselines_aggregate_stale_controls(self):
        current = self.current_state()
        payload = self.payload_for(current)
        changed_raw = dict(current.raw_fields)
        changed_raw["kid_vorname"] = "Grace"
        changed_raw["illness"] = "Different condition"
        period_type = self.public_context()[1]
        changed_periods = (
            period_type(17, (91, 92), (92,)),
            current.periods[1],
        )
        changed = self.current_state(
            raw_fields=changed_raw,
            periods=changed_periods,
        )
        error = self.assert_validation_error(
            self.validate(payload, changed),
            status=409,
            code="conflict",
            keys=("first_name", "illness", "swp.17"),
        )
        self.assertEqual(
            tuple(items[0].code for items in error.errors.values()),
            ("stale", "stale", "stale"),
        )

    def test_every_stale_control_has_its_exact_public_message(self):
        current = self.current_state()
        payload = self.payload_for(current)
        bad_token = "v1." + "Z" * 43
        for name in FIELD_NAMES:
            payload["field_baselines"][name] = bad_token
        payload["swp"][0]["baseline"] = bad_token
        payload["expected_number_version"] = 2
        payload["happy_cleaning"][0]["expected_assignment_version"] = 10

        error = self.validate(payload, current)
        self.assertEqual(
            tuple(error.errors),
            FIELD_NAMES
            + ("swp.17", "happy_cleaning_number", "happy_cleaning.42"),
        )
        for name in FIELD_NAMES:
            with self.subTest(field=name):
                item = error.errors[name][0]
                self.assertEqual(item.code, "stale")
                self.assertEqual(
                    item.message,
                    f"{FIELD_LABELS[name]} wurde zwischenzeitlich geändert. Bitte Seite neu laden.",
                )
        self.assertEqual(
            error.errors["swp.17"][0].message,
            "Diese Schwerpunkt-Einteilung wurde zwischenzeitlich geändert. Bitte Seite neu laden.",
        )
        self.assertEqual(
            error.errors["happy_cleaning_number"][0].message,
            "Die Happy-Cleaning-Nummer wurde zwischenzeitlich geändert. Bitte Seite neu laden.",
        )
        self.assertEqual(
            error.errors["happy_cleaning.42"][0].message,
            "Diese Happy-Cleaning-Einteilung wurde zwischenzeitlich geändert. Bitte Seite neu laden.",
        )

    def test_controlled_legacy_preserve_authenticates_exact_raw_context(self):
        current = self.current_state()
        raw = dict(current.raw_fields)
        raw["sex"] = "synthetic-legacy-sex"
        current = self.current_state(raw_fields=raw)
        payload = self.payload_for(current)
        sign_legacy = self.contract_api()[4]
        token = sign_legacy(
            turnus_id=161,
            child_id=7,
            field_name="sex",
            raw_storage_value="synthetic-legacy-sex",
        )
        payload["fields"]["sex"] = token
        validated = self.validate(payload, current)
        self.assertEqual(validated.storage_fields["sex"], "synthetic-legacy-sex")

        for wrong in (
            self.current_state(raw_fields={**raw, "sex": "other-legacy"}),
            self.current_state(child_id=8, raw_fields=raw),
            self.current_state(turnus_id=162, raw_fields=raw),
        ):
            with self.subTest(child=wrong.child_id, turnus=wrong.turnus_id):
                wrong_payload = self.payload_for(wrong)
                wrong_payload["fields"]["sex"] = token
                error = self.assert_validation_error(
                    self.validate(wrong_payload, wrong),
                    status=409,
                    code="conflict",
                    keys=("sex",),
                )
                self.assertEqual(error.errors["sex"][0].code, "stale")

    def test_multiple_swp_links_require_exact_preserve_baseline(self):
        period_type = self.public_context()[1]
        current = self.current_state(
            periods=(period_type(17, (91, 92, 93), (91, 92)),),
            events=(),
        )
        payload = self.payload_for(current)
        validated = self.validate(payload, current)
        self.assertEqual(validated.swp[0].target.kind, "preserve_legacy")
        self.assertEqual(validated.swp[0].current_focus_ids, (91, 92))

        payload["swp"][0]["target"]["token"] = "v1." + "Z" * 43
        error = self.assert_validation_error(
            self.validate(payload, current),
            status=409,
            code="conflict",
            keys=("swp.17",),
        )
        self.assertEqual(error.errors["swp.17"][0].code, "stale")

    def test_unchanged_invalid_email_reaches_contextual_compatibility_check(self):
        decoder_probe = KidEditDecoderTests.valid_payload()
        decoder_probe["fields"]["registrant_email"] = "legacy-invalid@"
        decoded = self.decode(decoder_probe)
        self.assertFalse(
            hasattr(decoded, "errors"),
            "decoder rejected unchanged legacy email before context exists",
        )

        current = self.current_state()
        raw = dict(current.raw_fields)
        raw["anmelder_email"] = "legacy-invalid@"
        current = self.current_state(raw_fields=raw)
        payload = self.payload_for(current)
        decoded = self.decode(payload)
        self.assertFalse(hasattr(decoded, "errors"), "decoder rejected unchanged legacy email")
        validated = self.public_context()[-1](decoded, current)
        self.assertEqual(
            validated.storage_fields["anmelder_email"],
            "legacy-invalid@",
        )

        payload["fields"]["registrant_email"] = "changed-invalid@"
        decoded = self.decode(payload)
        self.assertFalse(hasattr(decoded, "errors"), "decoder preempted contextual email check")
        error = self.assert_validation_error(
            self.public_context()[-1](decoded, current),
            status=422,
            code="validation_error",
            keys=("registrant_email",),
        )
        self.assertEqual(error.errors["registrant_email"][0].code, "invalid_email")

    def test_version_and_baseline_staleness_aggregate_with_safe_versions(self):
        current = self.current_state()
        payload = self.payload_for(current)
        payload["expected_edit_version"] = 3
        payload["expected_number_version"] = 2
        payload["happy_cleaning"][0]["expected_assignment_version"] = 10
        payload["happy_cleaning"][1]["expected_assignment_version"] = 1
        raw = dict(current.raw_fields)
        raw["illness"] = "Changed privately"
        changed = self.current_state(
            edit_version=5,
            number_version=4,
            raw_fields=raw,
        )
        error = self.assert_validation_error(
            self.validate(payload, changed),
            status=409,
            code="conflict",
            keys=(
                "illness",
                "happy_cleaning_number",
                "happy_cleaning.42",
                "happy_cleaning.43",
            ),
        )
        self.assertEqual(
            error.current_versions,
            {
                "edit": 5,
                "happy_cleaning_number": 4,
                "happy_cleaning": {"42": 11, "43": 0},
            },
        )
        rendered = repr(error)
        self.assertNotIn("Changed privately", rendered)
        self.assertNotIn("v1.", rendered)

    def test_edit_version_mismatch_with_matching_baselines_uses_form(self):
        current = self.current_state()
        payload = self.payload_for(current)
        payload["expected_edit_version"] = 3
        changed = self.current_state(edit_version=5)
        error = self.assert_validation_error(
            self.validate(payload, changed),
            status=409,
            code="conflict",
            keys=("_form",),
        )
        self.assertEqual(error.errors["_form"][0].code, "stale")
        self.assertEqual(error.current_versions["edit"], 5)

    def test_station_targets_require_number_on_number_and_each_event(self):
        current = self.current_state()
        payload = self.payload_for(current)
        payload["happy_cleaning_number"] = None
        payload["happy_cleaning"][1]["target"] = {
            "kind": "station",
            "station_id": 10,
        }
        error = self.assert_validation_error(
            self.validate(payload, current),
            status=422,
            code="validation_error",
            keys=(
                "happy_cleaning_number",
                "happy_cleaning.42",
                "happy_cleaning.43",
            ),
        )
        self.assertEqual(
            error.errors["happy_cleaning_number"][0].message,
            "Für eine Stationseinteilung ist eine Happy-Cleaning-Nummer erforderlich.",
        )
        for key in ("happy_cleaning.42", "happy_cleaning.43"):
            self.assertEqual(error.errors[key][0].code, "number_required")
            self.assertEqual(
                error.errors[key][0].message,
                "Vor der Stationseinteilung muss eine Happy-Cleaning-Nummer vergeben werden.",
            )

    def test_nested_snapshot_dtos_defensively_freeze_and_validate_ids(self):
        (
            state_type,
            period_type,
            event_type,
            target_type,
            _error_type,
            _validate,
        ) = self.public_context()
        available_focus_ids = [92, 91]
        current_focus_ids = [92]
        available_station_ids = [9, 8]
        period = period_type(17, available_focus_ids, current_focus_ids)
        event = event_type(
            42,
            available_station_ids,
            1,
            target_type(kind="station", station_id=8),
        )
        periods = [period]
        events = [event]
        raw_fields = dict(RAW_FIELDS)
        current = state_type(
            turnus_id=161,
            child_id=7,
            edit_version=4,
            number_version=3,
            happy_cleaning_number=42,
            raw_fields=raw_fields,
            periods=periods,
            events=events,
        )

        available_focus_ids.append(93)
        current_focus_ids.clear()
        available_station_ids.append(10)
        periods.clear()
        events.clear()
        raw_fields["kid_vorname"] = "Mutated"

        self.assertEqual(current.periods[0].available_focus_ids, (91, 92))
        self.assertEqual(current.periods[0].current_focus_ids, (92,))
        self.assertEqual(current.events[0].available_station_ids, (8, 9))
        self.assertEqual(current.raw_fields["kid_vorname"], "Ada")

        invalid_periods = (
            (17, (91, 91), (91,)),
            (17, (0,), ()),
            (17, (True,), ()),
            (17, (91,), (92,)),
        )
        for args in invalid_periods:
            with self.subTest(period=args):
                with self.assertRaises((TypeError, ValueError)):
                    period_type(*args)
        for station_ids in ((8, 8), (0,), (True,), (-1,), ("8",)):
            with self.subTest(station_ids=station_ids):
                with self.assertRaises((TypeError, ValueError)):
                    event_type(
                        42,
                        station_ids,
                        0,
                        target_type(kind="unassigned"),
                    )

    def test_current_event_version_is_zero_exactly_when_unassigned(self):
        (
            _state_type,
            _period_type,
            event_type,
            target_type,
            _error_type,
            _validate,
        ) = self.public_context()
        valid = (
            (0, target_type(kind="unassigned")),
            (1, target_type(kind="excused")),
            (7, target_type(kind="station", station_id=8)),
        )
        for version, target in valid:
            with self.subTest(valid_version=version, kind=target.kind):
                event = event_type(42, (8,), version, target)
                self.assertEqual(event.current_assignment_version, version)

        invalid = (
            (0, target_type(kind="excused")),
            (0, target_type(kind="station", station_id=8)),
            (1, target_type(kind="unassigned")),
        )
        for version, target in invalid:
            with self.subTest(invalid_version=version, kind=target.kind):
                with self.assertRaises((TypeError, ValueError)):
                    event_type(42, (8,), version, target)

    def test_stale_tokens_do_not_suppress_number_required_per_key(self):
        current = self.current_state()
        payload = self.payload_for(current)
        payload["happy_cleaning_number"] = None
        payload["expected_number_version"] = 2
        payload["happy_cleaning"][0]["expected_assignment_version"] = 10
        payload["happy_cleaning"][1]["target"] = {
            "kind": "station",
            "station_id": 10,
        }

        error = self.assert_validation_error(
            self.validate(payload, current),
            status=409,
            code="conflict",
            keys=(
                "happy_cleaning_number",
                "happy_cleaning.42",
                "happy_cleaning.43",
            ),
        )
        self.assertEqual(
            tuple(item.code for item in error.errors["happy_cleaning_number"]),
            ("stale", "number_required"),
        )
        self.assertEqual(
            tuple(item.code for item in error.errors["happy_cleaning.42"]),
            ("stale", "number_required"),
        )
        self.assertEqual(
            tuple(item.code for item in error.errors["happy_cleaning.43"]),
            ("number_required",),
        )

    def test_validation_is_deterministic_ordered_and_token_redacted(self):
        current = self.current_state()
        payload = self.payload_for(current)
        payload["swp"].reverse()
        payload["happy_cleaning"].reverse()
        first = self.validate(payload, current)
        second = self.validate(payload, current)
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.period_id for item in first.swp), (17, 18))
        self.assertEqual(tuple(item.event_id for item in first.happy_cleaning), (42, 43))
        rendered = repr(first)
        self.assertNotIn("Synthetic condition", rendered)
        self.assertNotIn("v1.", rendered)
        self.assertNotIn(LEGACY, rendered)
