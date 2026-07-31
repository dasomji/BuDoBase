from dataclasses import replace
from datetime import date
from queue import Queue
from threading import Barrier, Thread
from time import monotonic

from django.db import close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

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


class LockedAssignmentPlanTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=16203,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=16204,
            turnus_beginn=date(2026, 8, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=10,
        )
        self.sibling_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=20,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=30,
        )
        self.station = self.create_station(self.event, "Speisesaal", 1)
        self.target_station = self.create_station(self.event, "Küche", 2)
        self.sibling_station = self.create_station(
            self.sibling_event,
            "Gang",
            1,
        )
        self.other_station = self.create_station(
            self.other_event,
            "Foreign",
            1,
        )
        self.child = Kinder.objects.create(
            kid_index="KID-EDIT-ASSIGNMENT-PLAN",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            happy_cleaning_number=9,
        )
        self.second_child = Kinder.objects.create(
            kid_index="KID-EDIT-ASSIGNMENT-PLAN-SECOND",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            happy_cleaning_number=12,
        )
        self.foreign_child = Kinder.objects.create(
            kid_index="KID-EDIT-ASSIGNMENT-PLAN-FOREIGN",
            kid_vorname="Private",
            kid_nachname="Child",
            turnus=self.other_turnus,
            happy_cleaning_number=7,
        )
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    @staticmethod
    def create_station(event, name, position, max_kids=2):
        return HappyCleaningStation.objects.create(
            happy_cleaning=event,
            name=name,
            max_kids=max_kids,
            meeting_point="Tür",
            position=position,
        )

    @staticmethod
    def planner(**kwargs):
        from budo_app.happy_cleaning_assignment_commands import (
            plan_locked_assignment_change,
        )

        return plan_locked_assignment_change(**kwargs)

    @staticmethod
    def applier(**kwargs):
        from budo_app.happy_cleaning_assignment_commands import (
            apply_locked_assignment_change,
        )

        return apply_locked_assignment_change(**kwargs)

    @staticmethod
    def mutation_error_type():
        from budo_app.happy_cleaning_assignment_commands import (
            LockedMutationError,
        )

        return LockedMutationError

    def lock_state(
        self,
        *,
        child_id=None,
        event_id=None,
        station_ids=(),
    ):
        event_id = event_id or self.event.id
        child_id = child_id or self.child.id
        stations = {
            station.id: station
            for station in HappyCleaningStation.objects.select_for_update()
            .filter(pk__in=station_ids)
            .order_by("pk")
        }
        child = Kinder.objects.select_for_update().get(pk=child_id)
        current = (
            HappyCleaningAssignment.objects.select_for_update(of=("self",))
            .filter(happy_cleaning_id=event_id, child_id=child_id)
            .first()
        )
        event = HappyCleaning.objects.select_for_update().get(pk=event_id)
        return child, event, current, stations

    def plan(
        self,
        *,
        child,
        event,
        current,
        target_kind,
        station=None,
        expected_version,
    ):
        return self.planner(
            child=child,
            event=event,
            current_assignment=current,
            target_kind=target_kind,
            station=station,
            expected_version=expected_version,
        )

    def apply(
        self,
        *,
        child,
        event,
        current,
        plan,
        revision,
        target_station=None,
    ):
        return self.applier(
            child=child,
            event=event,
            current_assignment=current,
            plan=plan,
            event_revision=revision,
            target_station=target_station,
        )

    def create_assignment(
        self,
        *,
        child=None,
        event=None,
        station=None,
        excused=False,
        version=4,
    ):
        return HappyCleaningAssignment.objects.create(
            happy_cleaning=event or self.event,
            child=child or self.child,
            station=None if excused else (station or self.station),
            target_kind=(
                HappyCleaningAssignment.TargetKind.EXCUSED
                if excused
                else HappyCleaningAssignment.TargetKind.STATION
            ),
            version=version,
        )

    def assert_helper_owns_no_command_side_effects(self, expected_revision=10):
        self.event.refresh_from_db()
        self.assertEqual(self.event.revision, expected_revision)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def assert_neutral_error(self, error, code, current_version=None):
        self.assertIsInstance(error, self.mutation_error_type())
        self.assertEqual(error.code, code)
        self.assertEqual(error.current_version, current_version)
        self.assertEqual(getattr(error, "projection", {}), {})
        self.assertEqual(getattr(error, "details", {}), {})
        self.assertNotIn("Ada", repr(error))
        self.assertNotIn("Private", repr(error))
        self.assertNotIn("Speisesaal", repr(error))

    def test_create_station_assignment_uses_supplied_revision_and_markers(self):
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id,),
            )
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.station.id],
                expected_version=0,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            changed = self.apply(
                child=child,
                event=event,
                current=current,
                plan=plan,
                revision=event.revision,
                target_station=stations[self.station.id],
            )

        assignment = HappyCleaningAssignment.objects.get(
            happy_cleaning=self.event,
            child=self.child,
        )
        self.station.refresh_from_db()
        self.event.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(assignment.station_id, self.station.id)
        self.assertEqual(assignment.version, 11)
        self.assertTrue(self.station.has_ever_had_assignment)
        self.assertTrue(self.event.has_operational_activity)
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_move_assignment_updates_target_and_supplied_revision(self):
        assignment = self.create_assignment(version=4)
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id, self.target_station.id),
            )
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.target_station.id],
                expected_version=4,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            changed = self.apply(
                child=child,
                event=event,
                current=current,
                plan=plan,
                revision=event.revision,
                target_station=stations[self.target_station.id],
            )

        assignment.refresh_from_db()
        self.target_station.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(assignment.station_id, self.target_station.id)
        self.assertEqual(assignment.version, 11)
        self.assertTrue(self.target_station.has_ever_had_assignment)
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_excuse_assignment_clears_station_and_uses_supplied_revision(self):
        assignment = self.create_assignment(version=4)
        with transaction.atomic():
            child, event, current, _stations = self.lock_state(
                station_ids=(self.station.id,),
            )
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="excused",
                expected_version=4,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            changed = self.apply(
                child=child,
                event=event,
                current=current,
                plan=plan,
                revision=event.revision,
            )

        assignment.refresh_from_db()
        self.assertTrue(changed)
        self.assertTrue(assignment.is_excused)
        self.assertIsNone(assignment.station_id)
        self.assertEqual(assignment.version, 11)
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_remove_assignment_deletes_row_without_other_side_effects(self):
        assignment = self.create_assignment(excused=True, version=4)
        with transaction.atomic():
            child, event, current, _stations = self.lock_state()
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="unassigned",
                expected_version=4,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            changed = self.apply(
                child=child,
                event=event,
                current=current,
                plan=plan,
                revision=event.revision,
            )

        self.assertTrue(changed)
        self.assertFalse(
            HappyCleaningAssignment.objects.filter(pk=assignment.id).exists()
        )
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_same_overbooked_station_is_a_no_op(self):
        assignment = self.create_assignment(version=4)
        self.station.refresh_from_db()
        self.station.max_kids = 0
        self.station.save(update_fields=("max_kids",))

        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id,),
            )
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.station.id],
                expected_version=4,
            )
            changed = self.apply(
                child=child,
                event=event,
                current=current,
                plan=plan,
                revision=event.revision,
                target_station=stations[self.station.id],
            )

        assignment.refresh_from_db()
        self.assertFalse(plan.changed)
        self.assertFalse(changed)
        self.assertEqual(assignment.station_id, self.station.id)
        self.assertEqual(assignment.version, 4)
        self.assert_helper_owns_no_command_side_effects()

    def test_plan_rejects_turnus_and_exact_event_mismatches(self):
        cases = (
            (self.foreign_child.id, self.event.id, self.station.id),
            (self.child.id, self.other_event.id, self.other_station.id),
            (self.child.id, self.event.id, self.sibling_station.id),
        )
        for child_id, event_id, station_id in cases:
            with self.subTest(
                child_id=child_id,
                event_id=event_id,
                station_id=station_id,
            ):
                with transaction.atomic():
                    child, event, current, stations = self.lock_state(
                        child_id=child_id,
                        event_id=event_id,
                        station_ids=(station_id,),
                    )
                    with self.assertRaises(self.mutation_error_type()) as raised:
                        self.plan(
                            child=child,
                            event=event,
                            current=current,
                            target_kind="station",
                            station=stations[station_id],
                            expected_version=0,
                        )
                self.assert_neutral_error(raised.exception, "not_found")

    def test_expected_version_zero_matches_only_an_absent_assignment(self):
        with transaction.atomic():
            child, event, current, _stations = self.lock_state()
            with self.assertRaises(self.mutation_error_type()) as absent_error:
                self.plan(
                    child=child,
                    event=event,
                    current=current,
                    target_kind="excused",
                    expected_version=1,
                )
        self.assert_neutral_error(absent_error.exception, "stale", 0)

        self.create_assignment(version=4)
        with transaction.atomic():
            child, event, current, _stations = self.lock_state()
            with self.assertRaises(self.mutation_error_type()) as present_error:
                self.plan(
                    child=child,
                    event=event,
                    current=current,
                    target_kind="excused",
                    expected_version=0,
                )
        self.assert_neutral_error(present_error.exception, "stale", 4)

    def test_station_target_requires_number_and_available_capacity(self):
        self.child.happy_cleaning_number = None
        self.child.save(update_fields=("happy_cleaning_number",))
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id,),
            )
            with self.assertRaises(self.mutation_error_type()) as number_error:
                self.plan(
                    child=child,
                    event=event,
                    current=current,
                    target_kind="station",
                    station=stations[self.station.id],
                    expected_version=0,
                )
        self.assert_neutral_error(number_error.exception, "number_required")

        self.child.happy_cleaning_number = 9
        self.child.save(update_fields=("happy_cleaning_number",))
        self.create_assignment(
            child=self.second_child,
            station=self.station,
            version=4,
        )
        self.station.refresh_from_db()
        self.station.max_kids = 1
        self.station.save(update_fields=("max_kids",))
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id,),
            )
            with self.assertRaises(self.mutation_error_type()) as capacity_error:
                self.plan(
                    child=child,
                    event=event,
                    current=current,
                    target_kind="station",
                    station=stations[self.station.id],
                    expected_version=0,
                )
        self.assert_neutral_error(capacity_error.exception, "station_full")

    def test_plan_rejects_invalid_target_shapes(self):
        cases = (
            ("unknown", None),
            ("station", None),
            ("excused", self.station.id),
            ("unassigned", self.station.id),
        )
        for target_kind, station_id in cases:
            with self.subTest(target_kind=target_kind, station_id=station_id):
                ids = () if station_id is None else (station_id,)
                with transaction.atomic():
                    child, event, current, stations = self.lock_state(
                        station_ids=ids,
                    )
                    station = stations.get(station_id)
                    with self.assertRaises(self.mutation_error_type()) as raised:
                        self.plan(
                            child=child,
                            event=event,
                            current=current,
                            target_kind=target_kind,
                            station=station,
                            expected_version=0,
                        )
                self.assert_neutral_error(raised.exception, "validation_error")

    def test_apply_rejects_forged_mismatched_and_stale_plans(self):
        assignment = self.create_assignment(version=4)
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id, self.target_station.id),
            )
            valid = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.target_station.id],
                expected_version=4,
            )
            forged = replace(valid, target_kind="unknown")
            with self.assertRaises(self.mutation_error_type()) as forged_error:
                self.apply(
                    child=child,
                    event=event,
                    current=current,
                    plan=forged,
                    revision=event.revision,
                    target_station=stations[self.target_station.id],
                )
        self.assert_neutral_error(forged_error.exception, "plan_mismatch")

        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id, self.target_station.id),
            )
            other = Kinder.objects.select_for_update().get(pk=self.second_child.id)
            valid = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.target_station.id],
                expected_version=4,
            )
            with self.assertRaises(self.mutation_error_type()) as mismatch_error:
                self.apply(
                    child=other,
                    event=event,
                    current=current,
                    plan=valid,
                    revision=event.revision,
                    target_station=stations[self.target_station.id],
                )
        self.assert_neutral_error(mismatch_error.exception, "plan_mismatch")

        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id, self.target_station.id),
            )
            valid = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.target_station.id],
                expected_version=4,
            )
            current.version = 5
            current.save(update_fields=("version",))
            with self.assertRaises(self.mutation_error_type()) as stale_error:
                self.apply(
                    child=child,
                    event=event,
                    current=current,
                    plan=valid,
                    revision=event.revision,
                    target_station=stations[self.target_station.id],
                )
        self.assert_neutral_error(stale_error.exception, "stale", 5)
        assignment.refresh_from_db()
        self.assertEqual(assignment.station_id, self.station.id)
        self.assertEqual(assignment.version, 5)

    def test_apply_rejects_stale_and_forged_revisions_without_write(self):
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.target_station.id,),
            )
            target_station = stations[self.target_station.id]
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=target_station,
                expected_version=0,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            for supplied_revision in (event.revision - 1, event.revision + 1):
                with self.subTest(supplied_revision=supplied_revision):
                    with self.assertRaises(
                        self.mutation_error_type(),
                    ) as raised:
                        self.apply(
                            child=child,
                            event=event,
                            current=current,
                            plan=plan,
                            revision=supplied_revision,
                            target_station=target_station,
                        )
                    self.assert_neutral_error(
                        raised.exception,
                        "stale",
                        11,
                    )
                    self.assertFalse(HappyCleaningAssignment.objects.exists())

        self.assertFalse(HappyCleaningAssignment.objects.exists())
        self.target_station.refresh_from_db()
        self.assertFalse(self.target_station.has_ever_had_assignment)
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_apply_rejects_forged_same_event_target_station_without_write(self):
        with transaction.atomic():
            child, event, current, stations = self.lock_state(
                station_ids=(self.station.id, self.target_station.id),
            )
            plan = self.plan(
                child=child,
                event=event,
                current=current,
                target_kind="station",
                station=stations[self.target_station.id],
                expected_version=0,
            )
            event.revision += 1
            event.save(update_fields=("revision",))
            with self.assertRaises(self.mutation_error_type()) as raised:
                self.apply(
                    child=child,
                    event=event,
                    current=current,
                    plan=plan,
                    revision=event.revision,
                    target_station=stations[self.station.id],
                )

        self.assert_neutral_error(raised.exception, "plan_mismatch")
        self.assertFalse(HappyCleaningAssignment.objects.exists())
        self.station.refresh_from_db()
        self.target_station.refresh_from_db()
        self.assertFalse(self.station.has_ever_had_assignment)
        self.assertFalse(self.target_station.has_ever_had_assignment)
        self.assert_helper_owns_no_command_side_effects(expected_revision=11)

    def test_caller_rollback_restores_assignment_and_activity_markers(self):
        with self.assertRaisesRegex(RuntimeError, "aggregate rejected"):
            with transaction.atomic():
                child, event, current, stations = self.lock_state(
                    station_ids=(self.station.id,),
                )
                plan = self.plan(
                    child=child,
                    event=event,
                    current=current,
                    target_kind="station",
                    station=stations[self.station.id],
                    expected_version=0,
                )
                event.revision += 1
                event.save(update_fields=("revision",))
                self.apply(
                    child=child,
                    event=event,
                    current=current,
                    plan=plan,
                    revision=event.revision,
                    target_station=stations[self.station.id],
                )
                raise RuntimeError("aggregate rejected")

        self.station.refresh_from_db()
        self.event.refresh_from_db()
        self.assertFalse(HappyCleaningAssignment.objects.exists())
        self.assertFalse(self.station.has_ever_had_assignment)
        self.assertFalse(self.event.has_operational_activity)
        self.assert_helper_owns_no_command_side_effects()


@skipUnlessDBFeature("has_select_for_update")
class LockedAssignmentFinalSeatRaceTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL is required for row-lock contention.")
        self.turnus = Turnus.objects.create(
            turnus_nr=16205,
            turnus_beginn=date(2026, 9, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=10,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Final seat",
            max_kids=1,
            meeting_point="Door",
            position=1,
        )
        self.children = [
            Kinder.objects.create(
                kid_index=f"KID-EDIT-FINAL-SEAT-{index}",
                kid_vorname=f"Child {index}",
                kid_nachname="Race",
                turnus=self.turnus,
                happy_cleaning_number=index,
            )
            for index in (1, 2)
        ]

    def test_public_plan_and_apply_serialize_final_seat_without_deadlock(self):
        from budo_app.happy_cleaning_assignment_commands import (
            LockedMutationError,
            apply_locked_assignment_change,
            plan_locked_assignment_change,
        )

        barrier = Barrier(2)
        outcomes = Queue()

        def compete(child_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    with connections["default"].cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '5s'")
                        cursor.execute("SET LOCAL statement_timeout = '10s'")
                    station = (
                        HappyCleaningStation.objects.select_for_update()
                        .get(pk=self.station.id)
                    )
                    child = Kinder.objects.select_for_update().get(pk=child_id)
                    current = (
                        HappyCleaningAssignment.objects.select_for_update(
                            of=("self",),
                        )
                        .filter(
                            happy_cleaning_id=self.event.id,
                            child_id=child_id,
                        )
                        .first()
                    )
                    event = HappyCleaning.objects.select_for_update().get(
                        pk=self.event.id,
                    )
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
                outcomes.put("ok")
            except LockedMutationError as error:
                outcomes.put(error.code)
            except Exception as error:  # Preserve a bounded, diagnostic failure.
                outcomes.put(f"exception:{type(error).__name__}")
            finally:
                connections.close_all()

        threads = [
            Thread(target=compete, args=(child.id,), daemon=True)
            for child in self.children
        ]
        for thread in threads:
            thread.start()
        deadline = monotonic() + 20
        for thread in threads:
            thread.join(timeout=max(0, deadline - monotonic()))

        self.assertTrue(
            all(not thread.is_alive() for thread in threads),
            "final-seat contenders exceeded the bounded watchdog",
        )
        observed = [outcomes.get_nowait() for _thread in threads]
        self.assertCountEqual(observed, ["ok", "station_full"])
        self.assertEqual(
            HappyCleaningAssignment.objects.filter(
                happy_cleaning=self.event,
                station=self.station,
            ).count(),
            1,
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.revision, 11)
