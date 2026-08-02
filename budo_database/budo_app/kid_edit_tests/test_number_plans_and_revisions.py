from dataclasses import replace
from datetime import date
from queue import Queue
from threading import Event, Thread
from time import monotonic

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from budo_app.happy_cleaning_assignment_commands import (
    AssignmentCommandError,
    apply_locked_child_number,
    assign_missing_numbers,
    set_child_number,
)
from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Turnus,
)
from budo_app.happy_cleaning_commands import CommandContext


class LockedChildNumberPlanTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=162,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=163,
            turnus_beginn=date(2026, 8, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=4,
        )
        self.child = Kinder.objects.create(
            kid_index="KID-EDIT-NUMBER-PLAN",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            happy_cleaning_number=9,
        )
        self.foreign_child = Kinder.objects.create(
            kid_index="KID-EDIT-NUMBER-PLAN-FOREIGN",
            kid_vorname="Private",
            kid_nachname="Child",
            turnus=self.other_turnus,
            happy_cleaning_number=11,
        )
        self.actor = User.objects.create_user(username="number-plan-actor")
        self.actor.profil.turnus = self.turnus
        self.actor.profil.rufname = "Planner Actor"
        self.actor.profil.save(update_fields=("turnus", "rufname"))
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    @staticmethod
    def plan_number(**kwargs):
        from budo_app.happy_cleaning_assignment_commands import (
            plan_locked_child_number,
        )

        return plan_locked_child_number(**kwargs)

    def locked_plan(self, *, child, number, expected_version=1):
        return self.plan_number(
            child=child,
            turnus_id=self.turnus.id,
            number=number,
            expected_version=expected_version,
        )

    @staticmethod
    def mutation_error_type():
        from budo_app.happy_cleaning_assignment_commands import (
            LockedMutationError,
        )

        return LockedMutationError

    def command_context(self, request_id):
        return CommandContext(
            turnus=self.turnus,
            actor_id=self.actor.id,
            actor_label="Planner Actor",
            request_id=request_id,
            client_ip=None,
            user_agent="number-plan-test",
        )

    def assert_no_command_side_effects(self):
        self.event.refresh_from_db()
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_valid_plan_can_be_applied_without_command_side_effects(self):
        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.locked_plan(child=child, number=7)
            changed = apply_locked_child_number(child=child, plan=plan)

        self.child.refresh_from_db()
        self.assertTrue(plan.changed)
        self.assertTrue(changed)
        self.assertEqual(self.child.happy_cleaning_number, 7)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assert_no_command_side_effects()

    def test_plan_rechecks_turnus_and_expected_version(self):
        cases = (
            (self.foreign_child, 1, "not_found"),
            (self.child, 8, "stale"),
        )
        for child_record, expected_version, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with transaction.atomic():
                    child = Kinder.objects.select_for_update().get(
                        pk=child_record.id,
                    )
                    with self.assertRaises(self.mutation_error_type()) as raised:
                        self.locked_plan(
                            child=child,
                            number=7,
                            expected_version=expected_version,
                        )
                self.assertEqual(raised.exception.code, expected_code)
                self.assertEqual(
                    raised.exception.current_version,
                    1 if expected_code == "stale" else None,
                )
                self.assertEqual(getattr(raised.exception, "projection", {}), {})
                self.assertEqual(getattr(raised.exception, "details", {}), {})
                self.assertNotIn("Private", repr(raised.exception))
                self.assertNotIn("Ada", repr(raised.exception))

        self.child.refresh_from_db()
        self.foreign_child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.foreign_child.happy_cleaning_number, 11)

    def test_plan_accepts_positive_or_null_and_rejects_other_values(self):
        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            clear_plan = self.locked_plan(child=child, number=None)

        self.assertTrue(clear_plan.changed)
        self.assertIsNone(clear_plan.number)

        for invalid_number in (0, -1, True, "7"):
            with self.subTest(number=invalid_number):
                with transaction.atomic():
                    child = Kinder.objects.select_for_update().get(pk=self.child.id)
                    with self.assertRaises(self.mutation_error_type()) as raised:
                        self.locked_plan(child=child, number=invalid_number)
                self.assertEqual(raised.exception.code, "validation_error")
                self.assertIsNone(raised.exception.current_version)
                self.assertEqual(getattr(raised.exception, "projection", {}), {})
                self.assertEqual(getattr(raised.exception, "details", {}), {})

        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.child.happy_cleaning_number_version, 1)

    def test_plan_reports_a_canonical_no_op(self):
        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.locked_plan(child=child, number=9)
            changed = apply_locked_child_number(child=child, plan=plan)

        self.child.refresh_from_db()
        self.assertFalse(plan.changed)
        self.assertFalse(changed)
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.child.happy_cleaning_number_version, 1)
        self.assert_no_command_side_effects()

    def test_plan_rejects_a_number_occupied_in_current_locked_state(self):
        Kinder.objects.create(
            kid_index="KID-EDIT-NUMBER-PLAN-OCCUPIED",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            happy_cleaning_number=7,
        )

        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            with self.assertRaises(self.mutation_error_type()) as raised:
                self.locked_plan(child=child, number=7)

        self.assertEqual(raised.exception.code, "duplicate_number")
        self.assertEqual(raised.exception.current_version, 1)
        self.assertEqual(getattr(raised.exception, "projection", {}), {})
        self.assertEqual(getattr(raised.exception, "details", {}), {})
        self.assertNotIn("Grace", repr(raised.exception))
        self.assertNotIn("neighborhood", repr(raised.exception))
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.child.happy_cleaning_number_version, 1)
        self.assert_no_command_side_effects()

    def test_apply_rejects_a_plan_for_another_child(self):
        other_child = Kinder.objects.create(
            kid_index="KID-EDIT-NUMBER-PLAN-OTHER",
            kid_vorname="Katherine",
            kid_nachname="Johnson",
            turnus=self.turnus,
            happy_cleaning_number=12,
        )

        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            other = Kinder.objects.select_for_update().get(pk=other_child.id)
            plan = self.locked_plan(child=child, number=7)
            with self.assertRaises(self.mutation_error_type()) as raised:
                apply_locked_child_number(child=other, plan=plan)

        self.assertEqual(raised.exception.code, "plan_mismatch")
        self.child.refresh_from_db()
        other_child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(other_child.happy_cleaning_number, 12)

    def test_apply_rejects_child_state_changed_since_planning(self):
        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.locked_plan(child=child, number=7)
            child.happy_cleaning_number = 8
            child.happy_cleaning_number_version = 2
            child.save(update_fields=(
                "happy_cleaning_number",
                "happy_cleaning_number_version",
            ))
            with self.assertRaises(self.mutation_error_type()) as raised:
                apply_locked_child_number(child=child, plan=plan)

        self.assertEqual(raised.exception.code, "stale")
        self.assertEqual(raised.exception.current_version, 2)
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 8)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)

    def test_apply_has_no_raw_number_bypass(self):
        with transaction.atomic():
            child = Kinder.objects.select_for_update().get(pk=self.child.id)
            try:
                apply_locked_child_number(child=child, number=7)
            except TypeError:
                rejected = True
            else:
                rejected = False
            transaction.set_rollback(True)

        self.assertTrue(rejected)

    def test_apply_rejects_forged_plan_target_values_before_writing(self):
        for invalid_number in (True, "7", 0, -1):
            with self.subTest(number=invalid_number):
                with transaction.atomic():
                    child = Kinder.objects.select_for_update().get(pk=self.child.id)
                    valid_plan = self.locked_plan(child=child, number=7)
                    forged_plan = replace(valid_plan, number=invalid_number)
                    try:
                        with transaction.atomic():
                            apply_locked_child_number(
                                child=child,
                                plan=forged_plan,
                            )
                    except self.mutation_error_type():
                        outcome = "rejected"
                    except Exception as error:
                        outcome = type(error).__name__
                    else:
                        outcome = "applied"

                    in_memory_state = (
                        child.happy_cleaning_number,
                        child.happy_cleaning_number_version,
                    )
                    database_state = Kinder.objects.filter(
                        pk=self.child.id,
                    ).values_list(
                        "happy_cleaning_number",
                        "happy_cleaning_number_version",
                    ).get()
                    transaction.set_rollback(True)

                self.assertEqual(in_memory_state, (9, 1))
                self.assertEqual(database_state, (9, 1))
                self.assertEqual(outcome, "rejected")

    def test_standalone_number_command_retains_stale_projection(self):
        with self.assertRaises(AssignmentCommandError) as raised:
            set_child_number(
                self.command_context("standalone-stale-projection"),
                self.child.id,
                7,
                expected_version=8,
            )

        self.assertEqual(raised.exception.code, "stale")
        self.assertEqual(raised.exception.current_version, 1)
        self.assertEqual(
            raised.exception.projection["child"],
            {
                "id": self.child.id,
                "full_name": "Ada Lovelace",
                "number": 9,
                "number_version": 1,
            },
        )

    def test_standalone_number_command_retains_duplicate_projection(self):
        Kinder.objects.create(
            kid_index="KID-EDIT-NUMBER-CONTROL-OCCUPIED",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            happy_cleaning_number=7,
        )

        with self.assertRaises(AssignmentCommandError) as raised:
            set_child_number(
                self.command_context("standalone-duplicate-projection"),
                self.child.id,
                7,
                expected_version=1,
            )

        self.assertEqual(raised.exception.code, "duplicate_number")
        self.assertEqual(
            raised.exception.projection["child"]["full_name"],
            "Ada Lovelace",
        )
        neighborhood = raised.exception.projection["neighborhood"]
        occupied = next(item for item in neighborhood if item["number"] == 7)
        self.assertEqual(occupied["child"]["display_name"], "Grace Hopper")


class AffectedEventRevisionCoordinatorTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=164,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=165,
            turnus_beginn=date(2026, 8, 1),
        )
        self.first_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=4,
        )
        self.second_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=8,
        )
        self.foreign_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=12,
        )

    @staticmethod
    def bump_revisions(**kwargs):
        from budo_app.happy_cleaning_assignment_commands import (
            bump_locked_event_revisions_once,
        )

        return bump_locked_event_revisions_once(**kwargs)

    def test_number_and_same_assignment_event_share_one_revision_bump(self):
        with transaction.atomic():
            revisions = self.bump_revisions(
                turnus_id=self.turnus.id,
                number_changed=True,
                assignment_event_ids=(self.first_event.id,),
            )

        self.first_event.refresh_from_db()
        self.second_event.refresh_from_db()
        self.foreign_event.refresh_from_db()
        self.assertEqual(
            revisions,
            [
                (self.first_event.id, 5),
                (self.second_event.id, 9),
            ],
        )
        self.assertEqual(self.first_event.revision, 5)
        self.assertEqual(self.second_event.revision, 9)
        self.assertEqual(self.foreign_event.revision, 12)

    def test_empty_affected_event_set_is_a_no_op(self):
        with transaction.atomic():
            revisions = self.bump_revisions(
                turnus_id=self.turnus.id,
                number_changed=False,
                assignment_event_ids=(),
            )

        self.first_event.refresh_from_db()
        self.second_event.refresh_from_db()
        self.assertEqual(revisions, [])
        self.assertEqual(self.first_event.revision, 4)
        self.assertEqual(self.second_event.revision, 8)


@skipUnlessDBFeature("has_select_for_update_nowait")
class EventRevisionLockOrderPostgreSQLTests(TransactionTestCase):
    reset_sequences = True
    worker_timeout = 20

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Deterministic row-lock evidence requires PostgreSQL.")
        self.turnus = Turnus.objects.create(
            turnus_nr=166,
            turnus_beginn=date(2026, 7, 1),
        )
        self.actor = User.objects.create_user(username="event-lock-order-actor")
        self.actor.profil.turnus = self.turnus
        self.actor.profil.rufname = "Lock Actor"
        self.actor.profil.save(update_fields=("turnus", "rufname"))
        self.lower_pk_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=4,
        )
        self.higher_pk_hc1 = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=8,
        )
        station = HappyCleaningStation.objects.create(
            happy_cleaning=self.higher_pk_hc1,
            name="Speisesaal",
            max_kids=2,
            meeting_point="Tür",
            position=1,
        )
        self.child = Kinder.objects.create(
            kid_index="KID-EDIT-EVENT-LOCK-ORDER",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            anwesend=True,
        )
        self.assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.higher_pk_hc1,
            station=station,
            child=self.child,
            version=self.higher_pk_hc1.revision,
        )
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    def context(self):
        return CommandContext(
            turnus=self.turnus,
            actor_id=self.actor.id,
            actor_label="Lock Actor",
            request_id="batch-event-lock-order",
            client_ip=None,
            user_agent="event-lock-order-test",
        )

    def wait_until_backend_is_blocked(self, backend_pid, outcomes, label):
        deadline = monotonic() + 10
        polling_pause = Event()
        last_activity = None
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    """
                    SELECT state, wait_event_type, wait_event
                    FROM pg_stat_activity
                    WHERE pid = %s
                    """,
                    (backend_pid,),
                )
                activity = cursor.fetchone()
            last_activity = activity
            if activity is not None and activity[1] == "Lock":
                return
            if label in outcomes:
                self.fail(
                    f"{label} exited before lock wait: {outcomes[label]}."
                )
            polling_pause.wait(timeout=0.01)
        self.fail(
            f"Backend {backend_pid} did not reach a lock wait; "
            f"last activity was {last_activity}."
        )

    @staticmethod
    def worker(operation, backend_pids, outcomes, label):
        close_old_connections()
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('lock_timeout', %s, false)",
                    ("15000ms",),
                )
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, false)",
                    ("18000ms",),
                )
                cursor.execute("SELECT pg_backend_pid()")
                backend_pids.put((label, cursor.fetchone()[0]))
            operation()
            outcomes[label] = "ok"
        except BaseException as error:
            outcomes[label] = type(error).__name__
        finally:
            connections.close_all()

    def test_batch_hc1_and_coordinator_share_ascending_event_lock_order(self):
        backend_pids = Queue()
        outcomes = {}
        requested_assignments = [
            {
                "child_id": self.child.id,
                "number": 1,
                "expected_version": 1,
            }
        ]

        batch = Thread(
            target=self.worker,
            args=(
                lambda: assign_missing_numbers(
                    self.context(),
                    self.higher_pk_hc1.id,
                    requested_assignments,
                ),
                backend_pids,
                outcomes,
                "batch",
            ),
            daemon=True,
            name="number-batch-lock-order",
        )
        coordinator = Thread(
            target=self.worker,
            args=(
                lambda: self._coordinate_revisions(),
                backend_pids,
                outcomes,
                "coordinator",
            ),
            daemon=True,
            name="event-coordinator-lock-order",
        )

        with transaction.atomic():
            HappyCleaningAssignment.objects.select_for_update().get(
                pk=self.assignment.id,
            )
            batch.start()
            batch_label, batch_pid = backend_pids.get(timeout=10)
            self.assertEqual(batch_label, "batch")
            self.wait_until_backend_is_blocked(
                batch_pid,
                outcomes,
                "batch",
            )

            coordinator.start()
            coordinator_label, coordinator_pid = backend_pids.get(timeout=10)
            self.assertEqual(coordinator_label, "coordinator")
            self.wait_until_backend_is_blocked(
                coordinator_pid,
                outcomes,
                "coordinator",
            )

        deadline = monotonic() + self.worker_timeout
        for thread in (batch, coordinator):
            thread.join(timeout=max(0, deadline - monotonic()))
        connections.close_all()

        alive = [
            thread.name
            for thread in (batch, coordinator)
            if thread.is_alive()
        ]
        self.assertEqual(alive, [], "Event-lock contention exceeded watchdog.")
        results = sorted(outcomes.items())
        self.assertEqual(results, [("batch", "ok"), ("coordinator", "ok")])

    def _coordinate_revisions(self):
        with transaction.atomic():
            AffectedEventRevisionCoordinatorTests.bump_revisions(
                turnus_id=self.turnus.id,
                number_changed=True,
                assignment_event_ids=(),
            )
