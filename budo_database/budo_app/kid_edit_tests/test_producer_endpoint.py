"""RED PostgreSQL integration contract for the atomic kid-edit producer (#166)."""

from copy import deepcopy
from datetime import date
import json
import re
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TransactionTestCase
from django.urls import Resolver404, resolve, reverse

from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.kid_edit_audit import validate_kid_edit_details
from budo_app.kid_edit_contracts import (
    FIELD_CONTRACTS,
    canonicalize_storage_value,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Turnus,
)


FIELD_NAMES = tuple(field.api_name for field in FIELD_CONTRACTS)
FINGERPRINT = re.compile(r"\Ahmac-sha256:v1:[0-9a-f]{64}\Z")
NOT_FOUND = {"ok": False, "code": "not_found"}
UPDATED_FIELDS = {
    "first_name": "Bea",
    "last_name": "Johnson",
    "sex": "female",
    "birthday": "2013-06-05",
    "stay_weeks": 2,
    "siblings": "Linus",
    "tent_request": "Mit Clara",
    "budo_experience": True,
    "social_security_number": "0506131234",
    "illness": "SYNTHETIC-UPDATED-ILLNESS",
    "drugs": "SYNTHETIC-UPDATED-DRUGS",
    "vegetarian": True,
    "special_food": "Keine Nüsse",
    "swimmer": "gut",
    "consent": True,
    "over_the_counter_medication": "Paracetamol",
    "prescription_medication": "Asthmaspray",
    "tetanus": "2025",
    "tick_vaccine": "vollständig",
    "organization": "Ferienverein",
    "registrant_first_name": "Augusta",
    "registrant_last_name": "Johnson",
    "registrant_email": "augusta@valid.test",
    "registrant_phone": "+43 660 123",
    "insured_with": "Augusta Johnson",
    "emergency_contacts": "Grace\n+43 660 456",
    "budo_family": "M",
}


class KidEditProducerFixture(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=166, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=167, turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(username="kid-edit-producer")
        self.user.profil.rufname = "Operator"
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("rufname", "turnus"))
        self.client.force_login(self.user)

        self.child = Kinder.objects.create(
            kid_index="KID-166-PRIMARY",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            rechnungsadresse="",
            rechnung_ort="",
            rechnung_land="",
            happy_cleaning_number=7,
        )
        self.foreign_child = Kinder.objects.create(
            kid_index="KID-166-FOREIGN",
            kid_vorname="FOREIGN-PRIVATE-FIRST",
            kid_nachname="FOREIGN-PRIVATE-LAST",
            illness="FOREIGN-PRIVATE-ILLNESS",
            turnus=self.other_turnus,
            anmelder_vorname="",
            anmelder_nachname="",
            rechnungsadresse="",
            rechnung_ort="",
            rechnung_land="",
        )

        periods = list(self.turnus.schwerpunktzeit_set.order_by("id"))
        self.period_one, self.period_two = periods[:2]
        self.focus_one = Schwerpunkte.objects.create(
            swp_name="Current focus", schwerpunktzeit=self.period_one,
        )
        self.focus_one_target = Schwerpunkte.objects.create(
            swp_name="Target focus", schwerpunktzeit=self.period_one,
        )
        self.focus_two_target = Schwerpunkte.objects.create(
            swp_name="Second target", schwerpunktzeit=self.period_two,
        )
        self.child.schwerpunkte.add(self.focus_one)

        self.events = [
            HappyCleaning.objects.create(
                turnus=self.turnus, display_number=index, revision=index * 10,
            )
            for index in (1, 2, 3)
        ]
        self.stations = []
        for event in self.events:
            self.stations.append((
                HappyCleaningStation.objects.create(
                    happy_cleaning=event,
                    name=f"Station {event.display_number}A",
                    max_kids=10,
                    meeting_point="Door",
                    position=1,
                ),
                HappyCleaningStation.objects.create(
                    happy_cleaning=event,
                    name=f"Station {event.display_number}B",
                    max_kids=10,
                    meeting_point="Door",
                    position=2,
                ),
            ))
        self.assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.events[0],
            station=self.stations[0][0],
            child=self.child,
            version=5,
        )
        self.foreign_event = HappyCleaning.objects.create(
            turnus=self.other_turnus, display_number=1,
        )
        self.foreign_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.foreign_event,
            name="FOREIGN-PRIVATE-STATION",
            max_kids=10,
            meeting_point="FOREIGN-PRIVATE-MEETING",
            position=1,
        )
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()
        cache.clear()
        super().tearDown()

    def endpoint(self, child_id=None):
        return f"/api/kids/{child_id or self.child.id}/edit/"

    def require_endpoint(self):
        try:
            match = resolve(self.endpoint())
        except Resolver404:
            self.fail("POST /api/kids/<positive-id>/edit/ is not implemented")
        self.assertEqual(match.route, "api/kids/<int:kid_id>/edit/")

    def read_payload(self, request_id):
        response = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "kid-edit"})
            + f"?id={self.child.id}"
        )
        self.assertEqual(response.status_code, 200)
        kid = response.json()["kid"]
        return {
            "request_id": request_id,
            "expected_edit_version": kid["edit_version"],
            "field_baselines": deepcopy(kid["field_baselines"]),
            "fields": deepcopy(kid["fields"]),
            "swp": [
                {
                    "period_id": period["id"],
                    "baseline": period["baseline"],
                    "target": deepcopy(period["target"]),
                }
                for period in kid["swp_periods"]
            ],
            "happy_cleaning_number": kid["happy_cleaning_number"]["value"],
            "expected_number_version": kid["happy_cleaning_number"]["version"],
            "happy_cleaning": [
                {
                    "event_id": event["id"],
                    "expected_assignment_version": event["assignment_version"],
                    "target": deepcopy(event["target"]),
                }
                for event in kid["happy_cleaning_events"]
            ],
        }

    def changed_payload(self, request_id):
        payload = self.read_payload(request_id)
        payload["fields"] = deepcopy(UPDATED_FIELDS)
        targets = {
            self.period_one.id: {
                "kind": "focus", "focus_id": self.focus_one_target.id,
            },
            self.period_two.id: {
                "kind": "focus", "focus_id": self.focus_two_target.id,
            },
        }
        for row in payload["swp"]:
            row["target"] = targets[row["period_id"]]
        payload["happy_cleaning_number"] = 42
        event_targets = {
            self.events[0].id: {
                "kind": "station", "station_id": self.stations[0][1].id,
            },
            self.events[1].id: {"kind": "excused"},
            self.events[2].id: {
                "kind": "station", "station_id": self.stations[2][0].id,
            },
        }
        for row in payload["happy_cleaning"]:
            row["target"] = event_targets[row["event_id"]]
        return payload

    def post(self, payload, *, child_id=None, client=None, **extra):
        return (client or self.client).post(
            self.endpoint(child_id),
            data=json.dumps(payload),
            content_type="application/json",
            **extra,
        )

    def parse_envelope(self, status, code, message):
        return {
            "ok": False,
            "code": code,
            "errors": {"_form": [{"code": code, "message": message}]},
            "replayed": False,
        }, status

    def domain_snapshot(self):
        child = Kinder.objects.get(pk=self.child.id)
        return {
            "child": tuple(
                canonicalize_storage_value(
                    field, getattr(child, field.storage_name),
                ).api_value
                for field in FIELD_CONTRACTS
            ),
            "versions": (
                child.edit_version,
                child.happy_cleaning_number,
                child.happy_cleaning_number_version,
            ),
            "focuses": tuple(sorted(child.schwerpunkte.values_list("id", flat=True))),
            "events": tuple(HappyCleaning.objects.filter(
                turnus=self.turnus,
            ).order_by("id").values_list("id", "revision")),
            "assignments": tuple(HappyCleaningAssignment.objects.filter(
                child=self.child,
            ).order_by("happy_cleaning_id").values_list(
                "happy_cleaning_id", "target_kind", "station_id", "version",
            )),
            "audit": AuditEvent.objects.count(),
            "ledger": HappyCleaningCommandRequest.objects.count(),
        }

    def assert_no_secrets(self, value):
        rendered = json.dumps(value, ensure_ascii=False)
        for secret in (
            "SYNTHETIC-UPDATED-ILLNESS", "SYNTHETIC-UPDATED-DRUGS",
            "FOREIGN-PRIVATE", "v1.", "before", "after",
        ):
            self.assertNotIn(secret, rendered)

class KidEditProducerEndpointTests(KidEditProducerFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor == "postgresql":
            print(f"PostgreSQL server version: {connection.pg_version}")

    def test_session_json_post_accepts_bootstrap_csrf_token(self):
        payload = self.read_payload("csrf-session-json-166")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_token = csrf_client.get(reverse("bootstrap-api")).json()["csrf_token"]

        response = self.post(
            payload,
            client=csrf_client,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "no_change")
        self.assert_no_secrets(response.json())

    def test_success_flashes_once_after_navigation_and_exact_replay_does_not_duplicate(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_token = csrf_client.get(reverse("bootstrap-api")).json()["csrf_token"]
        success_message = [{
            "text": "Alle Daten und Einteilungen wurden gespeichert.",
            "tags": "success",
        }]
        no_change_message = [{
            "text": "Keine Änderungen zum Speichern.",
            "tags": "info",
        }]

        updated = self.post(
            self.changed_payload("flash-updated-166"),
            client=csrf_client,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(updated.json()["result"], "updated")
        first_bootstrap = csrf_client.get(reverse("bootstrap-api")).json()
        self.assertEqual(first_bootstrap["messages"], success_message)
        self.assertEqual(
            csrf_client.get(reverse("bootstrap-api")).json()["messages"],
            [],
        )

        no_change_payload = self.read_payload("flash-no-change-166")
        no_change = self.post(
            no_change_payload,
            client=csrf_client,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        replayed = self.post(
            no_change_payload,
            client=csrf_client,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(no_change.json()["result"], "no_change")
        self.assertTrue(replayed.json()["replayed"])
        replay_bootstrap = csrf_client.get(reverse("bootstrap-api")).json()
        self.assertEqual(replay_bootstrap["messages"], no_change_message)
        self.assert_no_secrets(replay_bootstrap["messages"])

    def test_positive_child_route_enforces_auth_profile_turnus_csrf_and_parser(self):
        self.require_endpoint()
        payload = self.read_payload("boundary-1")
        anonymous = Client().post(
            self.endpoint(), data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(self.post(payload, client=csrf).status_code, 403)

        self.user.profil.turnus = None
        self.user.profil.save(update_fields=("turnus",))
        cache.clear()
        unavailable = self.post(payload)
        self.assertEqual((unavailable.status_code, unavailable.json()), (404, NOT_FOUND))
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        cache.clear()

        unsupported = self.client.post(
            self.endpoint(), data=json.dumps(payload), content_type="text/plain",
        )
        expected, status = self.parse_envelope(
            415, "unsupported_media_type", "Bitte JSON-Daten senden.",
        )
        self.assertEqual((unsupported.status_code, unsupported.json()), (status, expected))
        malformed = self.client.post(
            self.endpoint(), data="{SECRET-PARSE-VALUE", content_type="application/json",
        )
        expected, status = self.parse_envelope(
            400, "invalid_json", "Die Anfrage enthält kein gültiges JSON.",
        )
        self.assertEqual((malformed.status_code, malformed.json()), (status, expected))
        self.assertNotIn("SECRET-PARSE-VALUE", malformed.content.decode())

    def test_canonical_no_op_completes_one_minimal_ledger_only(self):
        self.require_endpoint()
        payload = self.read_payload("no-op-166")
        before = self.domain_snapshot()
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["result"], "no_change")
        self.assertFalse(body["replayed"])
        self.assertEqual(self.domain_snapshot()["child"], before["child"])
        self.assertEqual(self.domain_snapshot()["versions"], before["versions"])
        self.assertEqual(self.domain_snapshot()["events"], before["events"])
        self.assertEqual(AuditEvent.objects.count(), 0)
        self.assertEqual(self.published, [])
        ledger = HappyCleaningCommandRequest.objects.get(request_id="no-op-166")
        self.assertEqual((ledger.action, ledger.status_code), ("kid.edit", 200))
        self.assertRegex(ledger.fingerprint, FINGERPRINT)
        self.assertEqual(ledger.response, body)
        self.assert_no_secrets(ledger.response)

    def test_all_field_swp_number_and_assignment_changes_commit_once(self):
        self.require_endpoint()
        payload = self.changed_payload("all-changes-166")
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        expected_assignments = {
            str(self.events[0].id): 11,
            str(self.events[1].id): 21,
            str(self.events[2].id): 31,
        }
        expected_events = dict(expected_assignments)
        self.assertEqual(response.json(), {
            "ok": True,
            "result": "updated",
            "kid_id": self.child.id,
            "redirect": f"/kid_details/{self.child.id}",
            "versions": {
                "edit": 2,
                "happy_cleaning_number": 2,
                "happy_cleaning_assignments": expected_assignments,
                "happy_cleaning_events": expected_events,
            },
            "replayed": False,
        })
        child = Kinder.objects.get(pk=self.child.id)
        for field in FIELD_CONTRACTS:
            self.assertEqual(
                canonicalize_storage_value(
                    field, getattr(child, field.storage_name),
                ).api_value,
                UPDATED_FIELDS[field.api_name],
            )
        self.assertEqual(
            set(child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_one_target.id, self.focus_two_target.id},
        )
        self.assertEqual((child.edit_version, child.happy_cleaning_number,
                          child.happy_cleaning_number_version), (2, 42, 2))
        audit = AuditEvent.objects.get(action="kid.edit")
        self.assertEqual(audit.request_id, "all-changes-166")
        self.assertEqual(validate_kid_edit_details(audit.details), audit.details)
        self.assertEqual(audit.details["before"]["fields"]["first_name"], "Ada")
        self.assertEqual(audit.details["after"]["fields"]["first_name"], "Bea")
        ledger = HappyCleaningCommandRequest.objects.get(request_id="all-changes-166")
        self.assertEqual((ledger.status_code, ledger.response), (200, response.json()))
        self.assertRegex(ledger.fingerprint, FINGERPRINT)
        self.assertEqual(len(self.published), 6)
        for callback in self.published:
            self.assertEqual(
                set(callback),
                {"kind", "happy_cleaning_id", "revision", "request_id"},
            )
            self.assertIn(callback["kind"], {"child_number", "assignment"})
            self.assertEqual(callback["request_id"], "all-changes-166")
            self.assert_no_secrets(callback)

    def test_exact_replay_and_request_key_action_or_payload_conflicts(self):
        self.require_endpoint()
        payload = self.read_payload("replay-166")
        created = self.post(payload)
        replayed = self.post(payload)
        self.assertEqual((created.status_code, replayed.status_code), (200, 200))
        expected = deepcopy(created.json())
        expected["replayed"] = True
        self.assertEqual(replayed.json(), expected)
        self.assertEqual(HappyCleaningCommandRequest.objects.filter(
            request_id="replay-166",
        ).count(), 1)

        changed = deepcopy(payload)
        changed["fields"]["first_name"] = "Different"
        conflict = self.post(changed)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "request_id_conflict")
        self.assertEqual(conflict.json()["errors"]["_form"], [{
            "code": "request_id_conflict",
            "message": (
                "Diese Speicheranfrage wurde bereits mit anderen Daten verwendet. "
                "Bitte Seite neu laden."
            ),
        }])

        HappyCleaningCommandRequest.objects.create(
            turnus=self.turnus,
            actor_id=self.user.id,
            request_id="action-conflict-166",
            action="happy_cleaning.child_number.change",
            response={"ok": True},
        )
        action_payload = self.read_payload("action-conflict-166")
        action_conflict = self.post(action_payload)
        self.assertEqual(action_conflict.status_code, 409)
        self.assertEqual(action_conflict.json()["code"], "request_id_conflict")

    def test_locked_multi_error_is_field_addressed_and_changes_nothing(self):
        self.require_endpoint()
        payload = self.read_payload("multi-error-166")
        payload["fields"]["last_name"] = ""
        Kinder.objects.filter(pk=self.child.id).update(
            kid_vorname="CONCURRENT-PRIVATE-FIRST",
            edit_version=2,
            happy_cleaning_number_version=2,
        )
        self.child.schwerpunkte.remove(self.focus_one)
        self.child.schwerpunkte.add(self.focus_one_target)
        HappyCleaningAssignment.objects.filter(pk=self.assignment.id).update(version=6)
        before = self.domain_snapshot()
        response = self.post(payload)
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["code"], "conflict")
        self.assertEqual(tuple(body["errors"]), (
            "first_name", "last_name", f"swp.{self.period_one.id}",
            "happy_cleaning_number", f"happy_cleaning.{self.events[0].id}",
        ))
        self.assertEqual(body["current_versions"], {
            "edit": 2,
            "happy_cleaning_number": 2,
            "happy_cleaning": {str(self.events[0].id): 6,
                               str(self.events[1].id): 0,
                               str(self.events[2].id): 0},
        })
        self.assertTrue(body["reload_required"])
        self.assertFalse(body["replayed"])
        self.assertEqual(self.domain_snapshot()["child"], before["child"])
        self.assertEqual(self.domain_snapshot()["versions"], before["versions"])
        self.assertEqual(self.domain_snapshot()["focuses"], before["focuses"])
        self.assertEqual(self.domain_snapshot()["assignments"], before["assignments"])
        self.assertEqual(AuditEvent.objects.count(), 0)
        self.assertNotIn("CONCURRENT-PRIVATE-FIRST", response.content.decode())

    def test_foreign_and_missing_children_or_targets_are_neutral_and_label_free(self):
        self.require_endpoint()
        payload = self.read_payload("foreign-child-166")
        foreign = self.post(payload, child_id=self.foreign_child.id)
        missing = self.post(payload, child_id=9_999_999)
        self.assertEqual((foreign.status_code, foreign.json()), (404, NOT_FOUND))
        self.assertEqual((missing.status_code, missing.json()), (404, NOT_FOUND))

        observed = []
        for request_id, station_id in (
            ("foreign-target-166", self.foreign_station.id),
            ("missing-target-166", 9_999_998),
        ):
            changed = self.read_payload(request_id)
            changed["happy_cleaning"][0]["target"] = {
                "kind": "station", "station_id": station_id,
            }
            result = self.post(changed)
            self.assertEqual(result.status_code, 422)
            observed.append(result.json())
        observed[1]["replayed"] = observed[0]["replayed"]
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[0]["errors"][f"happy_cleaning.{self.events[0].id}"], [{
            "code": "unavailable",
            "message": "Diese Auswahl ist nicht mehr verfügbar. Bitte Seite neu laden.",
        }])
        self.assert_no_secrets(observed)

    def test_every_transactional_failure_stage_rolls_back_every_effect(self):
        self.require_endpoint()
        stages = (
            ("scalar", mock.patch(
                "budo_app.kid_edit_writes.VersionedChildWrite.save_child",
                side_effect=RuntimeError("scalar-stage"),
            )),
            ("swp", mock.patch(
                "budo_app.kid_edit_writes.apply_locked_swp_change",
                side_effect=RuntimeError("swp-stage"),
            )),
            ("number", mock.patch(
                "budo_app.happy_cleaning_assignment_commands.apply_locked_child_number",
                side_effect=RuntimeError("number-stage"),
            )),
            ("assignment", mock.patch(
                "budo_app.happy_cleaning_assignment_commands.apply_locked_assignment_change",
                side_effect=RuntimeError("assignment-stage"),
            )),
            ("audit", mock.patch.object(
                AuditEvent.objects,
                "_create_validated_event",
                side_effect=RuntimeError("audit-stage"),
            )),
            ("ledger", mock.patch.object(
                HappyCleaningCommandRequest.objects,
                "create",
                side_effect=RuntimeError("ledger-stage"),
            )),
            ("callback-registration", mock.patch(
                "budo_app.happy_cleaning_assignment_publisher.transaction.on_commit",
                side_effect=RuntimeError("callback-registration-stage"),
            )),
        )
        baseline = self.domain_snapshot()
        for index, (stage, injected) in enumerate(stages):
            with self.subTest(stage=stage), injected, self.assertRaises(RuntimeError):
                self.post(self.changed_payload(f"injected-{index}-166"))
            self.assertEqual(self.domain_snapshot(), baseline)
            self.assertEqual(self.published, [])

    def test_committed_publisher_execution_is_best_effort(self):
        self.require_endpoint()

        def unavailable(_payload):
            raise RuntimeError("publisher unavailable")

        configure_assignment_publisher(unavailable)
        response = self.post(self.changed_payload("publisher-best-effort-166"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "updated")
        self.assertTrue(AuditEvent.objects.filter(
            action="kid.edit", request_id="publisher-best-effort-166",
        ).exists())
        self.assertTrue(HappyCleaningCommandRequest.objects.filter(
            request_id="publisher-best-effort-166",
        ).exists())
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 42)
