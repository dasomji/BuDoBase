from budo_app.test_membership_fixtures import approve_and_select_turnus
"""PostgreSQL race contracts for the atomic kid-edit producer (#166-02)."""

from copy import deepcopy
import json
from queue import Empty, Queue
from threading import Barrier, Thread
from time import monotonic

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections
from django.test import Client, skipUnlessDBFeature

from budo_app.happy_cleaning_assignment_commands import (
    AssignmentCommandError,
    assign_child,
    move_child,
    remove_child,
    set_child_number,
)
from budo_app.happy_cleaning_commands import (
    CommandError,
    CommandContext,
    create_event,
    delete_event,
)
from budo_app.kid_edit_tests.test_producer_endpoint import (
    KidEditProducerFixture,
)
from budo_app.kid_edit_writes import versioned_child_write
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    Kinder,
)


@skipUnlessDBFeature("has_select_for_update")
class KidEditProducerPostgreSQLRaceTests(KidEditProducerFixture):
    worker_timeout = 20

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor == "postgresql":
            print(f"PostgreSQL server version: {connection.pg_version}")

    def setUp(self):
        super().setUp()
        if connection.vendor != "postgresql":
            self.skipTest("Kid-edit races require PostgreSQL row locks.")
        self.other_user = User.objects.create_user(username="kid-edit-racer-two")
        approve_and_select_turnus(self.other_user, self.turnus)
        self.other_user.profil.rufname = "Other operator"
        self.other_user.profil.save()

    def context(self, request_id):
        return CommandContext(
            turnus=self.turnus,
            actor_id=self.other_user.id,
            actor_label="Other operator",
            request_id=request_id,
            client_ip=None,
            user_agent="kid-edit-race",
        )

    def http_operation(self, payload, *, child_id=None):
        client = Client()
        client.force_login(self.user)

        def operation():
            response = client.post(
                self.endpoint(child_id),
                data=json.dumps(payload),
                content_type="application/json",
            )
            return response.status_code, response.json()

        return operation

    def race(self, *operations):
        barrier = Barrier(len(operations))
        results = Queue()

        def worker(index, operation):
            response = None
            errors = []
            try:
                close_old_connections()
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('lock_timeout', %s, false)",
                        ("5000ms",),
                    )
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, false)",
                        ("12000ms",),
                    )
                barrier.wait(timeout=10)
                response = operation()
            except (AssignmentCommandError, CommandError) as error:
                response = ("domain_error", error.status, error.code)
            except BaseException as error:
                errors.append(type(error).__name__)
            finally:
                try:
                    connections.close_all()
                except BaseException as error:
                    errors.append(type(error).__name__)
                results.put((index, response, tuple(errors)))

        threads = [
            Thread(
                target=worker,
                args=(index, operation),
                daemon=True,
                name=f"kid-edit-race-{index}",
            )
            for index, operation in enumerate(operations)
        ]
        for thread in threads:
            thread.start()
        deadline = monotonic() + self.worker_timeout
        for thread in threads:
            thread.join(timeout=max(0, deadline - monotonic()))
        self.assertEqual(
            [thread.name for thread in threads if thread.is_alive()],
            [],
            "kid-edit race watchdog timed out",
        )
        outcomes = {}
        while True:
            try:
                index, response, errors = results.get_nowait()
            except Empty:
                break
            outcomes[index] = (response, errors)
        self.assertEqual(set(outcomes), set(range(len(operations))))
        error_types = tuple(
            error for _response, errors in outcomes.values() for error in errors
        )
        self.assertEqual(error_types, (), f"sanitized worker errors: {error_types}")
        ordered = [outcomes[index][0] for index in range(len(operations))]
        rendered = repr(ordered)
        for secret in (
            "SYNTHETIC-UPDATED-ILLNESS", "SYNTHETIC-UPDATED-DRUGS",
            "FOREIGN-PRIVATE", "v1.",
        ):
            self.assertNotIn(secret, rendered)
        return ordered

    @staticmethod
    def outcome_status(outcome):
        if isinstance(outcome, tuple) and outcome[0] == "domain_error":
            return outcome[1]
        if isinstance(outcome, tuple) and isinstance(outcome[0], int):
            return outcome[0]
        return 200

    def number_only_payload(self, request_id, number):
        payload = self.read_payload(request_id)
        payload["happy_cleaning_number"] = number
        return payload

    def assignment_payload(self, request_id, event, target):
        payload = self.read_payload(request_id)
        item = next(
            row for row in payload["happy_cleaning"]
            if row["event_id"] == event.id
        )
        item["target"] = target
        return payload

    def test_identical_same_key_is_exactly_once(self):
        payload = self.changed_payload("race-identical-166")
        outcomes = self.race(
            self.http_operation(payload),
            self.http_operation(deepcopy(payload)),
        )
        self.assertEqual([status for status, _body in outcomes], [200, 200])
        self.assertCountEqual(
            [body["replayed"] for _status, body in outcomes],
            [False, True],
        )
        self.assertEqual(HappyCleaningCommandRequest.objects.filter(
            request_id="race-identical-166", action="kid.edit",
        ).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(
            request_id="race-identical-166", action="kid.edit",
        ).count(), 1)
        self.assertEqual(len(self.published), 6)

    def test_different_payload_same_key_yields_one_conflict(self):
        first = self.read_payload("race-fingerprint-166")
        second = deepcopy(first)
        first["fields"]["first_name"] = "First winner"
        second["fields"]["first_name"] = "Second winner"
        outcomes = self.race(
            self.http_operation(first), self.http_operation(second),
        )
        self.assertCountEqual(
            [status for status, _body in outcomes], [200, 409],
        )
        conflict = next(body for status, body in outcomes if status == 409)
        self.assertEqual(conflict["code"], "request_id_conflict")
        self.assertEqual(HappyCleaningCommandRequest.objects.filter(
            request_id="race-fingerprint-166", action="kid.edit",
        ).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action="kid.edit").count(), 1)

    def test_distinct_same_child_edits_serialize_to_one_stale_loser(self):
        first = self.read_payload("race-child-a-166")
        second = deepcopy(first)
        second["request_id"] = "race-child-b-166"
        first["fields"]["first_name"] = "First serialized"
        second["fields"]["first_name"] = "Second serialized"
        outcomes = self.race(
            self.http_operation(first), self.http_operation(second),
        )
        self.assertCountEqual(
            [status for status, _body in outcomes], [200, 409],
        )
        loser = next(body for status, body in outcomes if status == 409)
        self.assertEqual(loser["errors"]["first_name"][0]["code"], "stale")
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self.assertIn(
            self.child.kid_vorname,
            {"First serialized", "Second serialized"},
        )
        self.assertEqual(AuditEvent.objects.filter(action="kid.edit").count(), 1)

    def test_number_races_preserve_version_and_uniqueness(self):
        aggregate = self.number_only_payload("race-number-aggregate-166", 42)
        outcomes = self.race(
            self.http_operation(aggregate),
            lambda: set_child_number(
                self.context("race-number-standalone-166"),
                self.child.id,
                43,
                1,
            ),
        )
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assertIn(self.child.happy_cleaning_number, {42, 43})
        self.assertCountEqual(
            [self.outcome_status(outcome) for outcome in outcomes],
            [200, 409],
        )
        self.assertEqual(len(self.published), 3)

        competitor = Kinder.objects.create(
            kid_index="RACE-NUMBER-COMPETITOR",
            kid_vorname="Competitor",
            kid_nachname="Child",
            turnus=self.turnus,
            happy_cleaning_number=90,
            anmelder_vorname="",
            anmelder_nachname="",
            rechnungsadresse="",
            rechnung_ort="",
            rechnung_land="",
        )
        aggregate = self.number_only_payload("race-number-unique-aggregate", 55)
        outcomes = self.race(
            self.http_operation(aggregate),
            lambda: set_child_number(
                self.context("race-number-unique-standalone"),
                competitor.id,
                55,
                1,
            ),
        )
        self.assertEqual(Kinder.objects.filter(
            turnus=self.turnus, happy_cleaning_number=55,
        ).count(), 1)
        self.assertIn(409, [self.outcome_status(outcome) for outcome in outcomes])

    def test_aggregate_and_standalone_final_seat_never_overbook(self):
        event = self.events[2]
        station = self.stations[2][0]
        station.max_kids = 1
        station.save(update_fields=("max_kids",))
        competitor = Kinder.objects.create(
            kid_index="RACE-SEAT-COMPETITOR",
            kid_vorname="Seat",
            kid_nachname="Competitor",
            turnus=self.turnus,
            happy_cleaning_number=88,
            anmelder_vorname="", anmelder_nachname="",
            rechnungsadresse="", rechnung_ort="", rechnung_land="",
        )
        aggregate = self.assignment_payload(
            "race-seat-aggregate-166",
            event,
            {"kind": "station", "station_id": station.id},
        )
        outcomes = self.race(
            self.http_operation(aggregate),
            lambda: assign_child(
                self.context("race-seat-standalone-166"),
                event.id,
                competitor.id,
                station.id,
            ),
        )
        self.assertEqual(HappyCleaningAssignment.objects.filter(
            station=station,
        ).count(), 1)
        self.assertIn(409, [self.outcome_status(outcome) for outcome in outcomes])

    def test_aggregate_serializes_with_standalone_move_and_remove(self):
        for operation_name in ("move", "remove"):
            with self.subTest(operation=operation_name):
                self.assignment.refresh_from_db()
                payload = self.assignment_payload(
                    f"race-{operation_name}-aggregate-166",
                    self.events[0],
                    {"kind": "excused"},
                )
                version = self.assignment.version
                if operation_name == "move":
                    standalone = lambda: move_child(
                        self.context("race-move-standalone-166"),
                        self.events[0].id,
                        self.child.id,
                        self.stations[0][1].id,
                        version,
                    )
                else:
                    standalone = lambda: remove_child(
                        self.context("race-remove-standalone-166"),
                        self.events[0].id,
                        self.child.id,
                        version,
                    )
                outcomes = self.race(self.http_operation(payload), standalone)
                self.assertIn(
                    409,
                    [self.outcome_status(outcome) for outcome in outcomes],
                )
                self.assertLessEqual(HappyCleaningAssignment.objects.filter(
                    child=self.child, happy_cleaning=self.events[0],
                ).count(), 1)
                if operation_name == "move":
                    assignment = HappyCleaningAssignment.objects.filter(
                        child=self.child, happy_cleaning=self.events[0],
                    ).first()
                    if assignment is None:
                        self.assignment = HappyCleaningAssignment.objects.create(
                            happy_cleaning=self.events[0], child=self.child,
                            station=self.stations[0][0],
                            version=HappyCleaning.objects.get(
                                pk=self.events[0].id,
                            ).revision,
                        )
                    else:
                        self.assignment = assignment

    def test_aggregate_serializes_with_event_create_and_delete(self):
        aggregate = self.number_only_payload("race-event-create-aggregate", 61)
        outcomes = self.race(
            self.http_operation(aggregate),
            lambda: create_event(self.context("race-event-create-standalone")),
        )
        self.assertTrue(all(
            self.outcome_status(outcome) in {200, 409}
            for outcome in outcomes
        ))
        created = HappyCleaning.objects.filter(
            turnus=self.turnus, display_number=4,
        ).get()

        aggregate = self.read_payload("race-event-delete-aggregate")
        outcomes = self.race(
            self.http_operation(aggregate),
            lambda: delete_event(
                self.context("race-event-delete-standalone"),
                created.id,
                created.revision,
            ),
        )
        self.assertTrue(all(
            self.outcome_status(outcome) in {200, 409}
            for outcome in outcomes
        ))
        self.assertLessEqual(HappyCleaning.objects.filter(pk=created.id).count(), 1)

    def test_aggregate_serializes_with_versioned_swp_writer(self):
        aggregate = self.read_payload("race-swp-aggregate-166")
        aggregate["fields"]["first_name"] = "Aggregate SWP winner"
        first_period = next(
            row for row in aggregate["swp"]
            if row["period_id"] == self.period_one.id
        )
        first_period["target"] = {
            "kind": "focus", "focus_id": self.focus_one_target.id,
        }

        def standalone():
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_nachname = "Standalone SWP winner"
                write.save_child(update_fields=("kid_nachname",))
                write.set_swp_links(
                    period_id=self.period_one.id,
                    focus_ids=(self.focus_one.id,),
                )

        outcomes = self.race(self.http_operation(aggregate), standalone)
        http_status = outcomes[0][0]
        self.assertIn(http_status, {200, 409})
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self.assertTrue(
            self.child.kid_vorname == "Aggregate SWP winner"
            or self.child.kid_nachname == "Standalone SWP winner"
        )
        self.assertLessEqual(AuditEvent.objects.filter(action="kid.edit").count(), 1)
