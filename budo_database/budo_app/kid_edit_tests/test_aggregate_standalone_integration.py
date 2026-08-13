from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date
from queue import Queue
from threading import Barrier, Event, Thread
from time import monotonic

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from budo_app.happy_cleaning_assignment_commands import (
    AssignmentCommandError,
    LockedMutationError,
    apply_locked_assignment_change,
    apply_locked_child_number,
    assign_child,
    assign_excused_child,
    bump_locked_event_revisions_once,
    move_child,
    move_child_to_excused,
    plan_locked_assignment_change,
    plan_locked_child_number,
    remove_child,
    set_child_number,
)
from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.happy_cleaning_commands import CommandContext
from budo_app.kid_edit_writes import (
    LockedSwpError,
    apply_locked_swp_change,
    plan_locked_swp_change,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)


@skipUnlessDBFeature("has_select_for_update")
class AggregateStandalonePostgreSQLIntegrationTests(TransactionTestCase):
    reset_sequences = True
    watchdog_seconds = 20

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL lock waits are required.")
        self.turnus = Turnus.objects.create(
            turnus_nr=16208,
            turnus_beginn=date(2026, 12, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=20,
        )
        self.station_a = self.create_station("A", 1, max_kids=2)
        self.station_b = self.create_station("B", 2, max_kids=2)
        self.period_1 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w1",
        )
        self.period_2 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w2",
        )
        self.focus_1 = Schwerpunkte.objects.create(
            swp_name="One",
            schwerpunktzeit=self.period_1,
        )
        self.focus_2 = Schwerpunkte.objects.create(
            swp_name="Two",
            schwerpunktzeit=self.period_2,
        )
        self.actor = User.objects.create_user(username="aggregate-race-actor")
        approve_and_select_turnus(self.actor, self.turnus)
        self.actor.profil.rufname = "Race Actor"
        self.actor.profil.save()
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    def create_station(self, name, position, max_kids=1):
        return HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name=name,
            max_kids=max_kids,
            meeting_point="Door",
            position=position,
        )

    def create_child(self, suffix, *, number=9):
        child = Kinder.objects.create(
            kid_index=f"AGGREGATE-STANDALONE-{suffix}",
            kid_vorname="Child",
            kid_nachname=suffix,
            turnus=self.turnus,
            happy_cleaning_number=number,
        )
        child.schwerpunkte.add(self.focus_1)
        return child

    def context(self, request_id):
        return CommandContext(
            turnus=self.turnus,
            actor_id=self.actor.id,
            actor_label="Race Actor",
            request_id=request_id,
            client_ip=None,
            user_agent="aggregate-race-test",
        )

    @staticmethod
    def configure_worker_connection():
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
            return cursor.fetchone()[0]

    def wait_for_lock(self, pid, outcomes, label):
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
                    (pid,),
                )
                last_activity = cursor.fetchone()
            if last_activity is not None and last_activity[1] == "Lock":
                return
            if label in outcomes:
                self.fail(f"{label} exited before lock wait: {outcomes[label]}")
            polling_pause.wait(timeout=0.01)
        self.fail(f"{label} did not reach lock wait: {last_activity}")

    def race_while_row_locked(
        self,
        *,
        model,
        row_id,
        aggregate,
        standalone,
        aggregate_first=False,
    ):
        barrier = Barrier(3)
        aggregate_waiting = Event()
        backend_pids = Queue()
        outcomes = {}

        def run(label, operation):
            close_old_connections()
            try:
                pid = self.configure_worker_connection()
                backend_pids.put((label, pid))
                barrier.wait(timeout=10)
                if label == "standalone" and aggregate_first:
                    if not aggregate_waiting.wait(timeout=10):
                        raise RuntimeError("aggregate lock-order watchdog")
                operation()
                outcomes[label] = "ok"
            except (
                AssignmentCommandError,
                LockedMutationError,
                LockedSwpError,
            ) as error:
                outcomes[label] = error.code
            except BaseException as error:
                outcomes[label] = f"exception:{type(error).__name__}"
            finally:
                connections.close_all()

        threads = [
            Thread(
                target=run,
                args=(label, operation),
                daemon=True,
                name=f"aggregate-standalone-{label}",
            )
            for label, operation in (
                ("aggregate", aggregate),
                ("standalone", standalone),
            )
        ]
        with transaction.atomic():
            model.objects.select_for_update().get(pk=row_id)
            for thread in threads:
                thread.start()
            pids = dict(backend_pids.get(timeout=10) for _thread in threads)
            barrier.wait(timeout=10)
            self.wait_for_lock(pids["aggregate"], outcomes, "aggregate")
            aggregate_waiting.set()
            self.wait_for_lock(pids["standalone"], outcomes, "standalone")

        deadline = monotonic() + self.watchdog_seconds
        for thread in threads:
            thread.join(timeout=max(0, deadline - monotonic()))
        self.assertEqual(
            [thread.name for thread in threads if thread.is_alive()],
            [],
            "aggregate/standalone contention exceeded watchdog",
        )
        self.assertNotIn("exception", " ".join(outcomes.values()))
        return outcomes

    def lock_swp_configuration(self):
        turnus = Turnus.objects.select_for_update().get(pk=self.turnus.id)
        periods = tuple(
            Schwerpunktzeit.objects.select_for_update()
            .filter(turnus=turnus)
            .order_by("id")
        )
        focuses = tuple(
            Schwerpunkte.objects.select_for_update()
            .filter(schwerpunktzeit_id__in=(period.id for period in periods))
            .order_by("id")
        )
        focuses_by_period = {period.id: [] for period in periods}
        for focus in focuses:
            focuses_by_period[focus.schwerpunktzeit_id].append(focus)
        configuration = tuple(
            (period, tuple(focuses_by_period[period.id]))
            for period in periods
        )
        return turnus, configuration

    @staticmethod
    def lock_active_swp_links(child, configuration):
        configured_ids = {
            focus.id
            for _period, focuses in configuration
            for focus in focuses
        }
        return frozenset(
            Kinder.schwerpunkte.through.objects.select_for_update(of=("self",))
            .filter(kinder_id=child.id, schwerpunkte_id__in=configured_ids)
            .order_by("id")
            .values_list("schwerpunkte_id", flat=True)
        )

    def aggregate_number_and_swp(self, child_id):
        with transaction.atomic():
            turnus, configuration = self.lock_swp_configuration()
            child = Kinder.objects.select_for_update().get(pk=child_id)
            active_ids = self.lock_active_swp_links(child, configuration)
            events = list(
                HappyCleaning.objects.select_for_update()
                .filter(turnus=turnus)
                .order_by("id")
            )
            number_plan = plan_locked_child_number(
                child=child,
                turnus_id=turnus.id,
                number=7,
                expected_version=1,
            )
            swp_plan = plan_locked_swp_change(
                child=child,
                turnus=turnus,
                focus_configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period={
                    self.period_1.id: (),
                    self.period_2.id: (self.focus_2.id,),
                },
                expected_version=1,
            )
            bump_locked_event_revisions_once(
                turnus_id=turnus.id,
                number_changed=number_plan.changed,
                assignment_event_ids=(),
            )
            apply_locked_child_number(child=child, plan=number_plan)
            apply_locked_swp_change(
                child=child,
                turnus=turnus,
                focus_configuration=configuration,
                active_link_ids=active_ids,
                plan=swp_plan,
            )
            if swp_plan.changed:
                child.edit_version += 1
                child.save(update_fields=("edit_version",))
            self.assertEqual(len(events), 1)

    def aggregate_assignment_only(self, *, child_id, target_kind, station_id=None):
        with transaction.atomic():
            station_ids = () if station_id is None else (station_id,)
            stations = {
                station.id: station
                for station in HappyCleaningStation.objects.select_for_update()
                .filter(pk__in=station_ids)
                .order_by("pk")
            }
            child = Kinder.objects.select_for_update().get(pk=child_id)
            current = (
                HappyCleaningAssignment.objects.select_for_update(of=("self",))
                .filter(happy_cleaning=self.event, child=child)
                .first()
            )
            event = HappyCleaning.objects.select_for_update().get(pk=self.event.id)
            target_station = stations.get(station_id)
            plan = plan_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                target_kind=target_kind,
                station=target_station,
                expected_version=0,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            apply_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                plan=plan,
                event_revision=event.revision,
                target_station=target_station,
            )

    def aggregate_existing_assignment(
        self,
        *,
        child_id,
        target_kind,
        target_station_id=None,
    ):
        observed_station_id = HappyCleaningAssignment.objects.only(
            "station_id",
        ).get(
            happy_cleaning=self.event,
            child_id=child_id,
        ).station_id
        station_ids = {
            station_id
            for station_id in (observed_station_id, target_station_id)
            if station_id is not None
        }

        with transaction.atomic():
            stations = {
                station.id: station
                for station in HappyCleaningStation.objects.select_for_update()
                .filter(pk__in=station_ids)
                .order_by("pk")
            }
            child = Kinder.objects.select_for_update().get(pk=child_id)
            current = HappyCleaningAssignment.objects.select_for_update(
                of=("self",),
            ).get(happy_cleaning=self.event, child=child)
            event = HappyCleaning.objects.select_for_update().get(pk=self.event.id)
            target_station = stations.get(target_station_id)
            plan = plan_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                target_kind=target_kind,
                station=target_station,
                expected_version=20,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            apply_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                plan=plan,
                event_revision=event.revision,
                target_station=target_station,
            )

    def test_number_aggregate_races_standalone_without_lost_state(self):
        child = self.create_child("NUMBER", number=9)
        outcomes = self.race_while_row_locked(
            model=Kinder,
            row_id=child.id,
            aggregate=lambda: self.aggregate_number_and_swp(child.id),
            standalone=lambda: set_child_number(
                self.context("race-number"),
                child.id,
                7,
                expected_version=1,
            ),
            aggregate_first=True,
        )

        child.refresh_from_db()
        self.event.refresh_from_db()
        self.assertCountEqual(outcomes.values(), ["ok", "stale"])
        self.assertEqual(child.happy_cleaning_number, 7)
        self.assertEqual(child.happy_cleaning_number_version, 2)
        self.assertEqual(self.event.revision, 21)
        if outcomes["aggregate"] == "ok":
            self.assertEqual(child.edit_version, 2)
            self.assertEqual(
                set(child.schwerpunkte.values_list("id", flat=True)),
                {self.focus_2.id},
            )
        else:
            self.assertEqual(child.edit_version, 1)
            self.assertEqual(
                set(child.schwerpunkte.values_list("id", flat=True)),
                {self.focus_1.id},
            )

    def test_caller_composes_number_and_assignment_with_one_revision_bump(self):
        child_record = self.create_child("COMPOSED", number=91)

        with transaction.atomic():
            station = HappyCleaningStation.objects.select_for_update().get(
                pk=self.station_a.id,
            )
            child = Kinder.objects.select_for_update().get(pk=child_record.id)
            current = HappyCleaningAssignment.objects.select_for_update(
                of=("self",),
            ).filter(happy_cleaning=self.event, child=child).first()
            event = HappyCleaning.objects.select_for_update().get(pk=self.event.id)
            number_plan = plan_locked_child_number(
                child=child,
                turnus_id=self.turnus.id,
                number=92,
                expected_version=1,
            )
            assignment_plan = plan_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                target_kind="station",
                station=station,
                expected_version=0,
            )
            apply_locked_child_number(child=child, plan=number_plan)
            revisions = bump_locked_event_revisions_once(
                turnus_id=self.turnus.id,
                number_changed=number_plan.changed,
                assignment_event_ids=(event.id,),
            )
            event.revision = dict(revisions)[event.id]
            apply_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                plan=assignment_plan,
                event_revision=event.revision,
                target_station=station,
            )

        child_record.refresh_from_db()
        self.event.refresh_from_db()
        assignment = HappyCleaningAssignment.objects.get(
            happy_cleaning=self.event,
            child=child_record,
        )
        self.assertEqual(revisions, [(self.event.id, 21)])
        self.assertEqual(child_record.happy_cleaning_number, 92)
        self.assertEqual(child_record.happy_cleaning_number_version, 2)
        self.assertEqual(self.event.revision, 21)
        self.assertEqual(assignment.version, self.event.revision)
        self.assertEqual(assignment.station_id, self.station_a.id)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_caller_composition_rolls_back_number_revision_and_assignment(self):
        child_record = self.create_child("COMPOSED-ROLLBACK", number=101)

        with self.assertRaisesRegex(RuntimeError, "aggregate rejected"):
            with transaction.atomic():
                station = HappyCleaningStation.objects.select_for_update().get(
                    pk=self.station_a.id,
                )
                child = Kinder.objects.select_for_update().get(pk=child_record.id)
                current = HappyCleaningAssignment.objects.select_for_update(
                    of=("self",),
                ).filter(happy_cleaning=self.event, child=child).first()
                event = HappyCleaning.objects.select_for_update().get(
                    pk=self.event.id,
                )
                number_plan = plan_locked_child_number(
                    child=child,
                    turnus_id=self.turnus.id,
                    number=102,
                    expected_version=1,
                )
                assignment_plan = plan_locked_assignment_change(
                    child=child,
                    event=event,
                    current_assignment=current,
                    target_kind="station",
                    station=station,
                    expected_version=0,
                )
                apply_locked_child_number(child=child, plan=number_plan)
                revisions = bump_locked_event_revisions_once(
                    turnus_id=self.turnus.id,
                    number_changed=number_plan.changed,
                    assignment_event_ids=(event.id,),
                )
                event.revision = dict(revisions)[event.id]
                apply_locked_assignment_change(
                    child=child,
                    event=event,
                    current_assignment=current,
                    plan=assignment_plan,
                    event_revision=event.revision,
                    target_station=station,
                )
                raise RuntimeError("aggregate rejected")

        child_record.refresh_from_db()
        self.event.refresh_from_db()
        self.station_a.refresh_from_db()
        self.assertEqual(child_record.happy_cleaning_number, 101)
        self.assertEqual(child_record.happy_cleaning_number_version, 1)
        self.assertEqual(self.event.revision, 20)
        self.assertFalse(
            HappyCleaningAssignment.objects.filter(
                happy_cleaning=self.event,
                child=child_record,
            ).exists()
        )
        self.assertFalse(self.station_a.has_ever_had_assignment)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_station_assigners_competing_for_final_seat_never_overfill(self):
        final_station = self.create_station("Final", 3, max_kids=1)
        aggregate_child = self.create_child("FINAL-AGGREGATE", number=41)
        standalone_child = self.create_child("FINAL-STANDALONE", number=42)

        outcomes = self.race_while_row_locked(
            model=HappyCleaningStation,
            row_id=final_station.id,
            aggregate=lambda: self.aggregate_assignment_only(
                child_id=aggregate_child.id,
                target_kind="station",
                station_id=final_station.id,
            ),
            standalone=lambda: assign_child(
                self.context("race-final-seat"),
                self.event.id,
                standalone_child.id,
                final_station.id,
            ),
        )

        self.event.refresh_from_db()
        assignments = HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            station=final_station,
        )
        self.assertCountEqual(outcomes.values(), ["ok", "station_full"])
        self.assertEqual(assignments.count(), 1)
        self.assertLessEqual(assignments.count(), final_station.max_kids)
        self.assertIn(
            assignments.get().child_id,
            (aggregate_child.id, standalone_child.id),
        )
        self.assertEqual(assignments.get().version, self.event.revision)
        self.assertEqual(self.event.revision, 21)

    def test_excused_creators_for_same_child_serialize_to_one_row(self):
        child = self.create_child("EXCUSED", number=51)

        outcomes = self.race_while_row_locked(
            model=Kinder,
            row_id=child.id,
            aggregate=lambda: self.aggregate_assignment_only(
                child_id=child.id,
                target_kind="excused",
            ),
            standalone=lambda: assign_excused_child(
                self.context("race-excused-create"),
                self.event.id,
                child.id,
            ),
        )

        self.event.refresh_from_db()
        assignments = HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            child=child,
        )
        self.assertCountEqual(outcomes.values(), ["ok", "stale"])
        self.assertEqual(assignments.count(), 1)
        assignment = assignments.get()
        self.assertTrue(assignment.is_excused)
        self.assertIsNone(assignment.station_id)
        self.assertEqual(assignment.version, self.event.revision)
        self.assertEqual(self.event.revision, 21)

    def test_competing_station_moves_serialize_without_lost_assignment(self):
        child = self.create_child("MOVE", number=61)
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            child=child,
            station=self.station_a,
            version=20,
        )
        standalone_target = self.create_station("Move standalone", 3, max_kids=2)

        outcomes = self.race_while_row_locked(
            model=HappyCleaningStation,
            row_id=self.station_a.id,
            aggregate=lambda: self.aggregate_existing_assignment(
                child_id=child.id,
                target_kind="station",
                target_station_id=self.station_b.id,
            ),
            standalone=lambda: move_child(
                self.context("race-move"),
                self.event.id,
                child.id,
                standalone_target.id,
                20,
            ),
        )

        assignment.refresh_from_db()
        self.event.refresh_from_db()
        self.assertCountEqual(outcomes.values(), ["ok", "stale"])
        self.assertEqual(
            assignment.station_id,
            self.station_b.id
            if outcomes["aggregate"] == "ok"
            else standalone_target.id,
        )
        self.assertEqual(assignment.version, 21)
        self.assertEqual(assignment.version, self.event.revision)
        self.assertEqual(
            HappyCleaningAssignment.objects.filter(
                happy_cleaning=self.event,
                child=child,
            ).count(),
            1,
        )
        self.assertLessEqual(self.station_b.assignments.count(), 2)
        self.assertLessEqual(standalone_target.assignments.count(), 2)

    def test_move_to_excused_race_serializes_to_one_coherent_row(self):
        child = self.create_child("MOVE-EXCUSED", number=71)
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            child=child,
            station=self.station_a,
            version=20,
        )

        outcomes = self.race_while_row_locked(
            model=HappyCleaningStation,
            row_id=self.station_a.id,
            aggregate=lambda: self.aggregate_existing_assignment(
                child_id=child.id,
                target_kind="excused",
            ),
            standalone=lambda: move_child_to_excused(
                self.context("race-move-excused"),
                self.event.id,
                child.id,
                20,
            ),
        )

        assignment.refresh_from_db()
        self.event.refresh_from_db()
        self.assertCountEqual(outcomes.values(), ["ok", "stale"])
        self.assertTrue(assignment.is_excused)
        self.assertIsNone(assignment.station_id)
        self.assertEqual(assignment.version, 21)
        self.assertEqual(assignment.version, self.event.revision)
        self.assertEqual(
            HappyCleaningAssignment.objects.filter(
                happy_cleaning=self.event,
                child=child,
            ).count(),
            1,
        )

    def test_remove_race_serializes_to_one_deletion_and_revision(self):
        child = self.create_child("REMOVE", number=81)
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            child=child,
            station=self.station_a,
            version=20,
        )

        outcomes = self.race_while_row_locked(
            model=HappyCleaningStation,
            row_id=self.station_a.id,
            aggregate=lambda: self.aggregate_existing_assignment(
                child_id=child.id,
                target_kind="unassigned",
            ),
            standalone=lambda: remove_child(
                self.context("race-remove"),
                self.event.id,
                child.id,
                20,
            ),
        )

        self.event.refresh_from_db()
        self.assertCountEqual(outcomes.values(), ["ok", "stale"])
        self.assertFalse(
            HappyCleaningAssignment.objects.filter(
                happy_cleaning=self.event,
                child=child,
            ).exists()
        )
        self.assertEqual(self.event.revision, 21)

    def test_helper_and_wrapper_assignment_shapes_match_but_side_effects_do_not(self):
        helper_child = self.create_child("PARITY-HELPER", number=31)
        wrapper_child = self.create_child("PARITY-WRAPPER", number=32)

        with transaction.atomic():
            station = HappyCleaningStation.objects.select_for_update().get(
                pk=self.station_a.id,
            )
            child = Kinder.objects.select_for_update().get(pk=helper_child.id)
            current = HappyCleaningAssignment.objects.select_for_update(
                of=("self",),
            ).filter(happy_cleaning=self.event, child=child).first()
            event = HappyCleaning.objects.select_for_update().get(pk=self.event.id)
            plan = plan_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                target_kind="station",
                station=station,
                expected_version=0,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            apply_locked_assignment_change(
                child=child,
                event=event,
                current_assignment=current,
                plan=plan,
                event_revision=event.revision,
                target_station=station,
            )

        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])
        wrapper_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=9,
            revision=20,
        )
        wrapper_station = HappyCleaningStation.objects.create(
            happy_cleaning=wrapper_event,
            name="Wrapper parity",
            max_kids=2,
            meeting_point="Door",
            position=1,
        )
        assign_child(
            self.context("parity-wrapper"),
            wrapper_event.id,
            wrapper_child.id,
            wrapper_station.id,
        )
        helper_assignment = HappyCleaningAssignment.objects.get(
            happy_cleaning=self.event,
            child=helper_child,
        )
        wrapper_assignment = HappyCleaningAssignment.objects.get(
            happy_cleaning=wrapper_event,
            child=wrapper_child,
        )
        self.assertEqual(
            (
                helper_assignment.target_kind,
                helper_assignment.version,
                helper_assignment.station is not None,
            ),
            (
                wrapper_assignment.target_kind,
                wrapper_assignment.version,
                wrapper_assignment.station is not None,
            ),
        )
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(HappyCleaningCommandRequest.objects.count(), 1)
        self.assertEqual(len(self.published), 1)
