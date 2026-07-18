"""PostgreSQL-only independent-connection races for issue #40."""

from datetime import date
from threading import Barrier, Thread

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from budo_app.happy_cleaning_assignment_commands import (
    AssignmentCommandError,
    assign_child,
    move_child,
    remove_child,
    set_child_number,
)
from budo_app.happy_cleaning_commands import CommandContext
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Turnus,
)


@skipUnlessDBFeature("has_select_for_update")
class HappyCleaningPostgreSQLRaceTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("SQLite does not validate SELECT FOR UPDATE races.")
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=20,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=1,
            meeting_point="Tür",
            position=1,
        )
        self.target_a = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Tür",
            position=2,
        )
        self.target_b = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Gang",
            max_kids=2,
            meeting_point="Tür",
            position=3,
        )
        self.children = [
            Kinder.objects.create(
                kid_index=f"RACE-{index}",
                kid_vorname=f"Child{index}",
                kid_nachname="Race",
                turnus=self.turnus,
                happy_cleaning_number=100 + index,
            )
            for index in range(1, 4)
        ]
        self.users = []
        for index in range(1, 4):
            user = User.objects.create_user(username=f"race-actor-{index}")
            user.profil.turnus = self.turnus
            user.profil.rufname = f"Actor {index}"
            user.profil.save(update_fields=("turnus", "rufname"))
            self.users.append(user)

    def context(self, index, request_id):
        user = self.users[index]
        return CommandContext(
            turnus=self.turnus,
            actor_id=user.id,
            actor_label=f"Actor {index + 1}",
            request_id=request_id,
            client_ip=None,
            user_agent="race-test",
        )

    def race(self, *operations):
        barrier = Barrier(len(operations))
        results = [None] * len(operations)

        def run(index, operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results[index] = ("ok", operation())
            except AssignmentCommandError as error:
                results[index] = (error.code, error.current_version)
            except Exception as error:  # surfaced with its concrete type below
                results[index] = ("exception", error)
            finally:
                connections.close_all()

        threads = [
            Thread(target=run, args=(index, operation), daemon=True)
            for index, operation in enumerate(operations)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        connections.close_all()
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        exceptions = [result[1] for result in results if result[0] == "exception"]
        if exceptions:
            raise exceptions[0]
        return results

    def test_two_children_competing_for_the_final_seat_never_overbook(self):
        results = self.race(
            lambda: assign_child(
                self.context(0, "final-seat-a"),
                self.event.id,
                self.children[0].id,
                self.station.id,
            ),
            lambda: assign_child(
                self.context(1, "final-seat-b"),
                self.event.id,
                self.children[1].id,
                self.station.id,
            ),
        )

        self.assertEqual(HappyCleaningAssignment.objects.filter(
            station=self.station,
        ).count(), 1)
        self.assertCountEqual([result[0] for result in results], ["ok", "station_full"])

    def test_one_child_competing_across_two_stations_has_one_assignment(self):
        results = self.race(
            lambda: assign_child(
                self.context(0, "same-child-a"),
                self.event.id,
                self.children[0].id,
                self.target_a.id,
            ),
            lambda: assign_child(
                self.context(1, "same-child-b"),
                self.event.id,
                self.children[0].id,
                self.target_b.id,
            ),
        )

        assignments = HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            child=self.children[0],
        )
        self.assertEqual(assignments.count(), 1)
        self.assertIn(assignments.get().station_id, (self.target_a.id, self.target_b.id))
        self.assertCountEqual([result[0] for result in results], ["ok", "stale"])

    def test_two_children_competing_for_one_number_preserve_uniqueness(self):
        Kinder.objects.filter(pk__in=[child.id for child in self.children[:2]]).update(
            happy_cleaning_number=None,
        )
        results = self.race(
            lambda: set_child_number(
                self.context(0, "number-race-a"),
                self.children[0].id,
                42,
                1,
            ),
            lambda: set_child_number(
                self.context(1, "number-race-b"),
                self.children[1].id,
                42,
                1,
            ),
        )

        self.assertEqual(Kinder.objects.filter(
            turnus=self.turnus,
            happy_cleaning_number=42,
        ).count(), 1)
        self.assertCountEqual([result[0] for result in results], ["ok", "duplicate_number"])

    def test_move_remove_and_move_move_races_keep_one_authoritative_state(self):
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.children[0],
            version=20,
        )
        move_remove = self.race(
            lambda: move_child(
                self.context(0, "move-remove-move"),
                self.event.id,
                self.children[0].id,
                self.target_a.id,
                20,
            ),
            lambda: remove_child(
                self.context(1, "move-remove-remove"),
                self.event.id,
                self.children[0].id,
                20,
            ),
        )
        self.assertEqual(sum(result[0] == "ok" for result in move_remove), 1)
        current = HappyCleaningAssignment.objects.filter(pk=assignment.id).first()
        self.assertTrue(current is None or current.station_id == self.target_a.id)

        if current is None:
            self.event.refresh_from_db()
            current = HappyCleaningAssignment.objects.create(
                happy_cleaning=self.event,
                station=self.station,
                child=self.children[0],
                version=self.event.revision,
            )
        else:
            HappyCleaningAssignment.objects.filter(pk=current.id).update(
                station=self.station,
            )
            current.refresh_from_db()
        move_move = self.race(
            lambda: move_child(
                self.context(0, "move-move-a"),
                self.event.id,
                self.children[0].id,
                self.target_a.id,
                current.version,
            ),
            lambda: move_child(
                self.context(1, "move-move-b"),
                self.event.id,
                self.children[0].id,
                self.target_b.id,
                current.version,
            ),
        )
        self.assertEqual(sum(result[0] == "ok" for result in move_move), 1)
        self.assertEqual(HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            child=self.children[0],
        ).count(), 1)

    def test_same_request_replays_once_while_different_requests_conflict(self):
        context = self.context(0, "same-request")
        same = self.race(
            lambda: assign_child(context, self.event.id, self.children[0].id, self.target_a.id),
            lambda: assign_child(context, self.event.id, self.children[0].id, self.target_a.id),
        )
        self.assertEqual([result[0] for result in same], ["ok", "ok"])
        self.assertEqual(HappyCleaningCommandRequest.objects.filter(
            request_id="same-request",
        ).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(request_id="same-request").count(), 1)

        different = self.race(
            lambda: assign_child(
                self.context(0, "different-request-a"),
                self.event.id,
                self.children[1].id,
                self.target_b.id,
            ),
            lambda: assign_child(
                self.context(0, "different-request-b"),
                self.event.id,
                self.children[1].id,
                self.target_b.id,
            ),
        )
        self.assertCountEqual([result[0] for result in different], ["ok", "stale"])
        self.assertEqual(HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            child=self.children[1],
        ).count(), 1)
