from datetime import date
from queue import Queue
from threading import Thread

from django.db import (
    DatabaseError,
    close_old_connections,
    connections,
    transaction,
)
from django.test import TransactionTestCase, skipUnlessDBFeature

from budo_app.models import Kinder, Schwerpunkte, Schwerpunktzeit, Turnus


EXPECTED_COVERED_KINDER_FIELDS = (
    "kid_vorname",
    "kid_nachname",
    "sex",
    "kid_birthday",
    "turnus_dauer",
    "geschwister",
    "zeltwunsch",
    "budo_erfahrung",
    "sozialversicherungsnr",
    "illness",
    "drugs",
    "vegetarisch",
    "special_food_description",
    "swimmer",
    "einverstaendnis_erklaerung",
    "rezeptfreie_medikamente",
    "rezept_medikamente",
    "tetanusimpfung",
    "zeckenimpfung",
    "anmelde_organisation",
    "anmelder_vorname",
    "anmelder_nachname",
    "anmelder_email",
    "anmelder_mobil",
    "hauptversichert_bei",
    "notfall_kontakte",
    "budo_family",
)


class VersionedChildWriteTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=161,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=162,
            turnus_beginn=date(2026, 8, 1),
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
        self.focus_1 = Schwerpunkte.objects.create(
            swp_name="Synthetic focus one",
            schwerpunktzeit=self.period_1,
        )
        self.focus_1_alternative = Schwerpunkte.objects.create(
            swp_name="Synthetic focus alternative",
            schwerpunktzeit=self.period_1,
        )
        self.focus_2 = Schwerpunkte.objects.create(
            swp_name="Synthetic focus two",
            schwerpunktzeit=self.period_2,
        )
        self.foreign_focus = Schwerpunkte.objects.create(
            swp_name="Synthetic foreign focus",
            schwerpunktzeit=self.other_period,
        )
        self.child = Kinder.objects.create(
            kid_index="SYNTHETIC-161-02",
            kid_vorname="Initial",
            kid_nachname="Child",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            illness="Initial condition",
            anwesend=False,
        )
        self.child.schwerpunkte.add(self.focus_1, self.foreign_focus)
        self.foreign_child = Kinder.objects.create(
            kid_index="SYNTHETIC-FOREIGN-161-02",
            kid_vorname="Foreign",
            kid_nachname="Child",
            turnus=self.other_turnus,
        )

    @staticmethod
    def protocol():
        from budo_app.kid_edit_writes import (
            COVERED_KINDER_FIELDS,
            ChildWriteScopeError,
            versioned_child_write,
        )

        return (
            COVERED_KINDER_FIELDS,
            ChildWriteScopeError,
            versioned_child_write,
        )

    def test_public_projection_matches_the_exact_157_scalar_membership(self):
        covered_fields, _scope_error, _versioned_child_write = self.protocol()

        self.assertEqual(tuple(covered_fields), EXPECTED_COVERED_KINDER_FIELDS)
        self.assertNotIn("happy_cleaning_number", covered_fields)
        self.assertNotIn("anwesend", covered_fields)
        self.assertNotIn("check_in_date", covered_fields)

    def test_multiple_scalar_and_swp_changes_bump_once(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.kid_vorname = "Updated"
            write.child.illness = "Updated condition"
            write.save_child(update_fields=("kid_vorname", "illness"))
            write.set_swp_links(
                period_id=self.period_1.id,
                focus_ids=(self.focus_1_alternative.id,),
            )
            write.set_swp_links(
                period_id=self.period_2.id,
                focus_ids=(self.focus_2.id,),
            )

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Updated")
        self.assertEqual(self.child.illness, "Updated condition")
        self.assertEqual(self.child.edit_version, 2)
        self.assertEqual(
            set(
                self.child.schwerpunkte.filter(
                    schwerpunktzeit__turnus=self.turnus,
                ).values_list("id", flat=True)
            ),
            {self.focus_1_alternative.id, self.focus_2.id},
        )
        self.assertTrue(
            self.child.schwerpunkte.filter(pk=self.foreign_focus.id).exists()
        )

    def test_canonical_scalar_and_swp_no_op_does_not_bump(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        Kinder.objects.filter(pk=self.child.id).update(illness="none")

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.kid_vorname = "Initial"
            write.child.illness = None
            write.save_child(update_fields=("kid_vorname", "illness"))
            write.set_swp_links(
                period_id=self.period_1.id,
                focus_ids=(self.focus_1.id,),
            )

        self.child.refresh_from_db()
        self.assertEqual(self.child.illness, "none")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    def test_outer_whitespace_equivalence_preserves_raw_storage(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        Kinder.objects.filter(pk=self.child.id).update(
            kid_vorname="  Initial  "
        )

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.kid_vorname = "Initial"
            write.save_child(update_fields=("kid_vorname",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "  Initial  ")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    def test_controlled_legacy_equivalence_preserves_raw_storage(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        Kinder.objects.filter(pk=self.child.id).update(sex="WeIbLiCh")

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.sex = "weiblich"
            write.save_child(update_fields=("sex",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.sex, "WeIbLiCh")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    def test_uncovered_only_change_does_not_bump_and_save_is_narrow(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        Kinder.objects.filter(pk=self.child.id).update(anwesend=True)

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.anwesend = False
            write.child.kid_vorname = "Narrow update"
            write.save_child(update_fields=("kid_vorname",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Narrow update")
        self.assertTrue(self.child.anwesend)
        self.assertEqual(self.child.edit_version, 2)

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ) as write:
            write.child.anwesend = False
            write.save_child(update_fields=("anwesend",))

        self.child.refresh_from_db()
        self.assertFalse(self.child.anwesend)
        self.assertEqual(self.child.edit_version, 2)

    def test_foreign_child_and_period_are_rejected_without_mutation(self):
        _covered_fields, scope_error, versioned_child_write = self.protocol()

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.foreign_child.id,
            ):
                pass

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_vorname = "Must roll back"
                write.save_child(update_fields=("kid_vorname",))
                write.set_swp_links(
                    period_id=self.other_period.id,
                    focus_ids=(self.foreign_focus.id,),
                )

        self.child.refresh_from_db()
        self.foreign_child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Initial")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(self.foreign_child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    def test_same_turnus_focus_from_another_period_is_rejected(self):
        _covered_fields, scope_error, versioned_child_write = self.protocol()

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_vorname = "Must roll back"
                write.save_child(update_fields=("kid_vorname",))
                write.set_swp_links(
                    period_id=self.period_1.id,
                    focus_ids=(self.focus_2.id,),
                )

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Initial")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    def test_explicit_edit_version_save_is_rejected_and_rolled_back(self):
        _covered_fields, scope_error, versioned_child_write = self.protocol()

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_vorname = "Must roll back"
                write.save_child(update_fields=("kid_vorname",))
                write.child.edit_version = 99
                write.save_child(update_fields=("edit_version",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Initial")
        self.assertEqual(self.child.edit_version, 1)

    def test_direct_edit_version_tampering_is_rejected_and_rolled_back(self):
        _covered_fields, scope_error, versioned_child_write = self.protocol()

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_vorname = "Must roll back"
                write.save_child(update_fields=("kid_vorname",))
                write.child.edit_version = 99
                write.child.save(update_fields=("edit_version",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Initial")
        self.assertEqual(self.child.edit_version, 1)

    def test_scope_mutation_is_rejected_and_rolled_back(self):
        _covered_fields, scope_error, versioned_child_write = self.protocol()

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.turnus = self.other_turnus
                write.save_child(update_fields=("turnus",))

        with self.assertRaises(scope_error):
            with versioned_child_write(
                turnus_id=self.turnus.id,
                child_id=self.child.id,
            ) as write:
                write.child.kid_vorname = "Must roll back"
                write.save_child(update_fields=("kid_vorname",))
                write.child.turnus = self.other_turnus
                write.child.save(update_fields=("turnus",))

        self.child.refresh_from_db()
        self.assertEqual(self.child.turnus_id, self.turnus.id)
        self.assertEqual(self.child.kid_vorname, "Initial")
        self.assertEqual(self.child.edit_version, 1)

    def test_injected_failure_rolls_back_fields_links_and_version(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()

        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            with transaction.atomic():
                with versioned_child_write(
                    turnus_id=self.turnus.id,
                    child_id=self.child.id,
                ) as write:
                    write.child.kid_nachname = "Must roll back"
                    write.save_child(update_fields=("kid_nachname",))
                    write.set_swp_links(
                        period_id=self.period_1.id,
                        focus_ids=(self.focus_1_alternative.id,),
                    )
                raise RuntimeError("synthetic failure")

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_nachname, "Child")
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_1.id, self.foreign_focus.id},
        )

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_context_holds_the_child_row_lock_until_exit(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        result = Queue()

        def compete_for_child_lock():
            close_old_connections()
            try:
                with transaction.atomic():
                    Kinder.objects.select_for_update(nowait=True).get(
                        pk=self.child.id,
                    )
                result.put("acquired")
            except DatabaseError:
                result.put("blocked")
            finally:
                connections.close_all()

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ):
            competitor = Thread(target=compete_for_child_lock, daemon=True)
            competitor.start()
            competitor.join(timeout=10)
            self.assertFalse(competitor.is_alive())
            self.assertEqual(result.get(timeout=1), "blocked")

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_context_holds_configuration_rows_until_exit(self):
        _covered_fields, _scope_error, versioned_child_write = self.protocol()
        probes = (
            ("turnus", Turnus, self.turnus.id),
            ("period", Schwerpunktzeit, self.period_1.id),
            ("focus", Schwerpunkte, self.focus_1.id),
        )

        with versioned_child_write(
            turnus_id=self.turnus.id,
            child_id=self.child.id,
        ):
            for label, model, row_id in probes:
                with self.subTest(configuration=label):
                    result = Queue()

                    def compete_for_configuration_lock(
                        model=model,
                        row_id=row_id,
                        result=result,
                    ):
                        close_old_connections()
                        try:
                            with transaction.atomic():
                                model.objects.select_for_update(
                                    nowait=True,
                                ).get(pk=row_id)
                            result.put("acquired")
                        except DatabaseError:
                            result.put("blocked")
                        finally:
                            connections.close_all()

                    competitor = Thread(
                        target=compete_for_configuration_lock,
                        daemon=True,
                    )
                    competitor.start()
                    competitor.join(timeout=10)
                    self.assertFalse(competitor.is_alive())
                    self.assertEqual(result.get(timeout=1), "blocked")
