from dataclasses import FrozenInstanceError, replace
from datetime import date

from django.db import transaction
from django.test import TransactionTestCase

from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaningCommandRequest,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)


class LockedSwpPlanTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=16206,
            turnus_beginn=date(2026, 10, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=16207,
            turnus_beginn=date(2026, 11, 1),
        )
        self.period_1 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w1",
        )
        self.period_2 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w2",
        )
        self.other_period = Schwerpunktzeit.objects.get(
            turnus=self.other_turnus,
            woche="w1",
        )
        self.focus_1 = self.create_focus(self.period_1, "First")
        self.focus_1_alternative = self.create_focus(
            self.period_1,
            "First alternative",
        )
        self.focus_2 = self.create_focus(self.period_2, "Second")
        self.foreign_focus = self.create_focus(
            self.other_period,
            "Foreign",
        )
        self.child = Kinder.objects.create(
            kid_index="KID-EDIT-SWP-PLAN",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            edit_version=7,
        )
        self.other_child = Kinder.objects.create(
            kid_index="KID-EDIT-SWP-PLAN-OTHER",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            edit_version=7,
        )
        self.foreign_child = Kinder.objects.create(
            kid_index="KID-EDIT-SWP-PLAN-FOREIGN",
            kid_vorname="Private",
            kid_nachname="Child",
            turnus=self.other_turnus,
            edit_version=3,
        )
        self.child.schwerpunkte.add(self.focus_1, self.foreign_focus)
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    @staticmethod
    def create_focus(period, name):
        return Schwerpunkte.objects.create(
            swp_name=name,
            schwerpunktzeit=period,
        )

    @staticmethod
    def seam():
        from budo_app.kid_edit_writes import (
            LockedSwpError,
            LockedSwpPlan,
            apply_locked_swp_change,
            plan_locked_swp_change,
        )

        return (
            LockedSwpError,
            LockedSwpPlan,
            plan_locked_swp_change,
            apply_locked_swp_change,
        )

    def lock_state(self, *, child_id=None, turnus_id=None):
        turnus_id = turnus_id or self.turnus.id
        child_id = child_id or self.child.id
        locked_turnus = Turnus.objects.select_for_update().get(pk=turnus_id)
        periods = tuple(
            Schwerpunktzeit.objects.select_for_update()
            .filter(turnus_id=turnus_id)
            .order_by("id")
        )
        configuration = []
        for period in periods:
            focuses = tuple(
                Schwerpunkte.objects.select_for_update()
                .filter(schwerpunktzeit_id=period.id)
                .order_by("id")
            )
            configuration.append((period, focuses))
        configuration = tuple(configuration)
        configured_ids = {
            focus.id
            for _period, focuses in configuration
            for focus in focuses
        }
        child = Kinder.objects.select_for_update().get(pk=child_id)
        through = Kinder.schwerpunkte.through
        active_link_ids = frozenset(
            through.objects.select_for_update(of=("self",))
            .filter(
                kinder_id=child.id,
                schwerpunkte_id__in=configured_ids,
            )
            .order_by("id")
            .values_list("schwerpunkte_id", flat=True)
        )
        return locked_turnus, configuration, child, active_link_ids

    def requested(self, *, period_1=(), period_2=()):
        return {
            self.period_1.id: tuple(period_1),
            self.period_2.id: tuple(period_2),
        }

    def plan(
        self,
        *,
        child,
        turnus,
        configuration,
        active_link_ids,
        requested_links_by_period,
        expected_version=None,
    ):
        _error, _plan_type, planner, _applier = self.seam()
        return planner(
            child=child,
            turnus=turnus,
            focus_configuration=configuration,
            active_link_ids=active_link_ids,
            requested_links_by_period=requested_links_by_period,
            expected_version=(
                child.edit_version
                if expected_version is None
                else expected_version
            ),
        )

    def apply(
        self,
        *,
        child,
        turnus,
        configuration,
        active_link_ids,
        plan,
    ):
        _error, _plan_type, _planner, applier = self.seam()
        return applier(
            child=child,
            turnus=turnus,
            focus_configuration=configuration,
            active_link_ids=active_link_ids,
            plan=plan,
        )

    def assert_neutral_error(self, error, code, current_version=None):
        error_type, _plan_type, _planner, _applier = self.seam()
        self.assertIsInstance(error, error_type)
        self.assertEqual(error.code, code)
        self.assertEqual(error.current_version, current_version)
        self.assertEqual(getattr(error, "projection", {}), {})
        self.assertEqual(getattr(error, "details", {}), {})
        self.assertNotIn("Ada", repr(error))
        self.assertNotIn("Private", repr(error))
        self.assertNotIn("Foreign", repr(error))

    def assert_no_helper_side_effects(self):
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def active_link_ids(self):
        return set(
            self.child.schwerpunkte.filter(
                schwerpunktzeit__turnus=self.turnus,
            ).values_list("id", flat=True)
        )

    def test_changed_plan_applies_only_active_through_row_diff(self):
        self.child.schwerpunkte.add(self.focus_2)
        through = Kinder.schwerpunkte.through
        retained_active_pk = through.objects.get(
            kinder_id=self.child.id,
            schwerpunkte_id=self.focus_2.id,
        ).pk
        retained_foreign_pk = through.objects.get(
            kinder_id=self.child.id,
            schwerpunkte_id=self.foreign_focus.id,
        ).pk

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                    period_2=(self.focus_2.id,),
                ),
            )
            changed = self.apply(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                plan=plan,
            )

        self.child.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(
            self.active_link_ids(),
            {self.focus_1_alternative.id, self.focus_2.id},
        )
        self.assertEqual(self.child.edit_version, 7)
        self.assertEqual(
            through.objects.get(
                kinder_id=self.child.id,
                schwerpunkte_id=self.focus_2.id,
            ).pk,
            retained_active_pk,
        )
        self.assertEqual(
            through.objects.get(
                kinder_id=self.child.id,
                schwerpunkte_id=self.foreign_focus.id,
            ).pk,
            retained_foreign_pk,
        )
        self.assert_no_helper_side_effects()

    def test_no_op_is_immutable_and_preserves_rows_and_version(self):
        through = Kinder.schwerpunkte.through
        active_pk = through.objects.get(
            kinder_id=self.child.id,
            schwerpunkte_id=self.focus_1.id,
        ).pk
        foreign_pk = through.objects.get(
            kinder_id=self.child.id,
            schwerpunkte_id=self.foreign_focus.id,
        ).pk

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1.id,),
                ),
            )
            _error, plan_type, _planner, _applier = self.seam()
            self.assertIsInstance(plan, plan_type)
            self.assertFalse(plan.changed)
            with self.assertRaises(FrozenInstanceError):
                plan.changed = True
            changed = self.apply(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                plan=plan,
            )

        self.child.refresh_from_db()
        self.assertFalse(changed)
        self.assertEqual(self.active_link_ids(), {self.focus_1.id})
        self.assertEqual(self.child.edit_version, 7)
        self.assertEqual(
            through.objects.get(
                kinder_id=self.child.id,
                schwerpunkte_id=self.focus_1.id,
            ).pk,
            active_pk,
        )
        self.assertEqual(
            through.objects.get(
                kinder_id=self.child.id,
                schwerpunkte_id=self.foreign_focus.id,
            ).pk,
            foreign_pk,
        )
        self.assert_no_helper_side_effects()

    def test_exact_current_same_period_multi_link_is_a_row_preserving_no_op(self):
        self.child.schwerpunkte.add(self.focus_1_alternative)
        through = Kinder.schwerpunkte.through
        original_rows = dict(
            through.objects.filter(kinder_id=self.child.id).values_list(
                "schwerpunkte_id",
                "id",
            )
        )

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(
                        self.focus_1.id,
                        self.focus_1_alternative.id,
                    ),
                ),
            )
            changed = self.apply(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                plan=plan,
            )

        self.child.refresh_from_db()
        self.assertFalse(plan.changed)
        self.assertFalse(changed)
        self.assertEqual(
            self.active_link_ids(),
            {self.focus_1.id, self.focus_1_alternative.id},
        )
        self.assertEqual(
            dict(
                through.objects.filter(kinder_id=self.child.id).values_list(
                    "schwerpunkte_id",
                    "id",
                )
            ),
            original_rows,
        )
        self.assertEqual(self.child.edit_version, 7)
        self.assert_no_helper_side_effects()

    def test_current_multi_link_period_is_preserved_while_other_period_changes(self):
        self.child.schwerpunkte.add(self.focus_1_alternative)
        through = Kinder.schwerpunkte.through
        retained_rows = {
            focus_id: row_id
            for focus_id, row_id in through.objects.filter(
                kinder_id=self.child.id,
                schwerpunkte_id__in=(
                    self.focus_1.id,
                    self.focus_1_alternative.id,
                    self.foreign_focus.id,
                ),
            ).values_list("schwerpunkte_id", "id")
        }

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(
                        self.focus_1.id,
                        self.focus_1_alternative.id,
                    ),
                    period_2=(self.focus_2.id,),
                ),
            )
            changed = self.apply(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                plan=plan,
            )

        self.child.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(
            self.active_link_ids(),
            {
                self.focus_1.id,
                self.focus_1_alternative.id,
                self.focus_2.id,
            },
        )
        self.assertEqual(
            {
                focus_id: row_id
                for focus_id, row_id in through.objects.filter(
                    kinder_id=self.child.id,
                    schwerpunkte_id__in=retained_rows,
                ).values_list("schwerpunkte_id", "id")
            },
            retained_rows,
        )
        self.assertEqual(self.child.edit_version, 7)
        self.assert_no_helper_side_effects()

    def test_caller_rollback_restores_active_and_foreign_links(self):
        with self.assertRaisesRegex(RuntimeError, "aggregate rejected"):
            with transaction.atomic():
                turnus, configuration, child, active_ids = self.lock_state()
                plan = self.plan(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    requested_links_by_period=self.requested(
                        period_1=(self.focus_1_alternative.id,),
                        period_2=(self.focus_2.id,),
                    ),
                )
                self.apply(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    plan=plan,
                )
                raise RuntimeError("aggregate rejected")

        self.child.refresh_from_db()
        self.assertEqual(self.active_link_ids(), {self.focus_1.id})
        self.assertTrue(
            self.child.schwerpunkte.filter(pk=self.foreign_focus.id).exists()
        )
        self.assertEqual(self.child.edit_version, 7)
        self.assert_no_helper_side_effects()

    def test_future_caller_can_coalesce_scalar_and_swp_into_one_version_bump(self):
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            child.kid_vorname = "Updated"
            child.save(update_fields=("kid_vorname",))
            self.apply(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                plan=plan,
            )
            child.edit_version += 1
            child.save(update_fields=("edit_version",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Updated")
        self.assertEqual(self.active_link_ids(), {self.focus_1_alternative.id})
        self.assertEqual(self.child.edit_version, 8)
        self.assert_no_helper_side_effects()

    def test_planner_rejects_child_turnus_and_version_mismatches_neutrally(self):
        cases = (
            (self.foreign_child.id, self.turnus.id, 3, "not_found", None),
            (self.child.id, self.other_turnus.id, 7, "not_found", None),
            (self.child.id, self.turnus.id, 6, "stale", 7),
        )
        for child_id, turnus_id, version, code, current_version in cases:
            with self.subTest(code=code, child_id=child_id, turnus_id=turnus_id):
                with transaction.atomic():
                    turnus, configuration, child, active_ids = self.lock_state(
                        child_id=child_id,
                        turnus_id=turnus_id,
                    )
                    with self.assertRaises(self.seam()[0]) as raised:
                        self.plan(
                            child=child,
                            turnus=turnus,
                            configuration=configuration,
                            active_link_ids=active_ids,
                            requested_links_by_period={
                                period.id: ()
                                for period, _focuses in configuration
                            },
                            expected_version=version,
                        )
                self.assert_neutral_error(
                    raised.exception,
                    code,
                    current_version,
                )

    def test_planner_rejects_invalid_configuration_and_exact_period_shape(self):
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            invalid_configuration = (
                configuration[0],
                (self.other_period, (self.foreign_focus,)),
            )
            with self.assertRaises(self.seam()[0]) as config_error:
                self.plan(
                    child=child,
                    turnus=turnus,
                    configuration=invalid_configuration,
                    active_link_ids=active_ids,
                    requested_links_by_period=self.requested(),
                )
        self.assert_neutral_error(config_error.exception, "validation_error")

        invalid_requests = (
            {self.period_1.id: (self.focus_1.id,)},
            {
                **self.requested(period_1=(self.focus_1.id,)),
                self.other_period.id: (),
            },
        )
        for requested in invalid_requests:
            with self.subTest(period_ids=tuple(requested)):
                with transaction.atomic():
                    turnus, configuration, child, active_ids = self.lock_state()
                    with self.assertRaises(self.seam()[0]) as period_error:
                        self.plan(
                            child=child,
                            turnus=turnus,
                            configuration=configuration,
                            active_link_ids=active_ids,
                            requested_links_by_period=requested,
                        )
                self.assert_neutral_error(
                    period_error.exception,
                    "validation_error",
                )

    def test_planner_rejects_foreign_focus_neutrally(self):
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            with self.assertRaises(self.seam()[0]) as raised:
                self.plan(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    requested_links_by_period=self.requested(
                        period_1=(self.foreign_focus.id,),
                    ),
                )
        self.assert_neutral_error(raised.exception, "not_found")

    def test_different_or_forged_multi_link_target_rejects_without_write(self):
        through = Kinder.schwerpunkte.through
        original_rows = dict(
            through.objects.filter(kinder_id=self.child.id).values_list(
                "schwerpunkte_id",
                "id",
            )
        )
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            with self.assertRaises(self.seam()[0]) as different_error:
                self.plan(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    requested_links_by_period=self.requested(
                        period_1=(
                            self.focus_1.id,
                            self.focus_1_alternative.id,
                        ),
                    ),
                )
        self.assert_neutral_error(different_error.exception, "validation_error")

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            valid = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            forged = replace(
                valid,
                target_link_ids=frozenset(
                    {self.focus_1.id, self.focus_1_alternative.id},
                ),
            )
            with self.assertRaises(self.seam()[0]) as forged_error:
                self.apply(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    plan=forged,
                )
        self.assert_neutral_error(forged_error.exception, "plan_mismatch")
        self.child.refresh_from_db()
        self.assertEqual(self.active_link_ids(), {self.focus_1.id})
        self.assertEqual(
            dict(
                through.objects.filter(kinder_id=self.child.id).values_list(
                    "schwerpunkte_id",
                    "id",
                )
            ),
            original_rows,
        )
        self.assertEqual(self.child.edit_version, 7)
        self.assert_no_helper_side_effects()

    def test_applier_rejects_mismatched_stale_and_forged_plans(self):
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            other_child = Kinder.objects.select_for_update().get(
                pk=self.other_child.id,
            )
            with self.assertRaises(self.seam()[0]) as mismatch_error:
                self.apply(
                    child=other_child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=frozenset(),
                    plan=plan,
                )
        self.assert_neutral_error(mismatch_error.exception, "plan_mismatch")

        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            child.edit_version = 8
            child.save(update_fields=("edit_version",))
            with self.assertRaises(self.seam()[0]) as stale_version_error:
                self.apply(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    plan=plan,
                )
        self.assert_neutral_error(stale_version_error.exception, "stale", 8)

        self.child.edit_version = 7
        self.child.save(update_fields=("edit_version",))
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            self.child.schwerpunkte.add(self.focus_2)
            stale_ids = frozenset({self.focus_1.id, self.focus_2.id})
            with self.assertRaises(self.seam()[0]) as stale_links_error:
                self.apply(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=stale_ids,
                    plan=plan,
                )
        self.assert_neutral_error(stale_links_error.exception, "stale", 7)

        self.child.schwerpunkte.remove(self.focus_2)
        with transaction.atomic():
            turnus, configuration, child, active_ids = self.lock_state()
            plan = self.plan(
                child=child,
                turnus=turnus,
                configuration=configuration,
                active_link_ids=active_ids,
                requested_links_by_period=self.requested(
                    period_1=(self.focus_1_alternative.id,),
                ),
            )
            forged = replace(
                plan,
                target_link_ids=frozenset(
                    {self.focus_1.id, self.focus_1_alternative.id},
                ),
            )
            with self.assertRaises(self.seam()[0]) as forged_error:
                self.apply(
                    child=child,
                    turnus=turnus,
                    configuration=configuration,
                    active_link_ids=active_ids,
                    plan=forged,
                )
        self.assert_neutral_error(forged_error.exception, "plan_mismatch")
        self.child.refresh_from_db()
        self.assertEqual(self.active_link_ids(), {self.focus_1.id})
        self.assertEqual(self.child.edit_version, 7)
        self.assertTrue(
            self.child.schwerpunkte.filter(pk=self.foreign_focus.id).exists()
        )
        self.assert_no_helper_side_effects()
