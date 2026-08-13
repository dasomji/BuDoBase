from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase

from budo_app.happy_cleaning_assignment_commands import set_child_number
from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.happy_cleaning_commands import CommandContext
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningCommandRequest,
    Kinder,
    Turnus,
)


class LockAssumingChildNumberMutationTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=162,
            turnus_beginn=date(2026, 7, 1),
        )
        self.actor = User.objects.create_user(username="kid-edit-helper-actor")
        approve_and_select_turnus(self.actor, self.turnus)
        self.actor.profil.rufname = "Helper Actor"
        self.actor.profil.save()
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=4,
        )
        self.child = Kinder.objects.create(
            kid_index="KID-EDIT-HELPER-162",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            happy_cleaning_number=9,
        )
        self.published = []
        configure_assignment_publisher(self.published.append)

    def tearDown(self):
        reset_assignment_publisher()

    @staticmethod
    def plan_locked_child_number(*, child, number):
        from budo_app.happy_cleaning_assignment_commands import (
            plan_locked_child_number,
        )

        return plan_locked_child_number(
            child=child,
            turnus_id=child.turnus_id,
            number=number,
            expected_version=child.happy_cleaning_number_version,
        )

    @staticmethod
    def apply_locked_child_number(*, child, plan):
        from budo_app.happy_cleaning_assignment_commands import (
            apply_locked_child_number,
        )

        return apply_locked_child_number(child=child, plan=plan)

    def test_locked_helper_commits_only_its_domain_mutation(self):
        with transaction.atomic():
            locked_child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.plan_locked_child_number(child=locked_child, number=7)
            changed = self.apply_locked_child_number(child=locked_child, plan=plan)

        self.child.refresh_from_db()
        self.event.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(self.child.happy_cleaning_number, 7)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_locked_helper_no_op_reports_false_without_side_effects(self):
        with transaction.atomic():
            locked_child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.plan_locked_child_number(child=locked_child, number=9)
            changed = self.apply_locked_child_number(child=locked_child, plan=plan)

        self.child.refresh_from_db()
        self.event.refresh_from_db()
        self.assertFalse(changed)
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.child.happy_cleaning_number_version, 1)
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_duplicate_number_restores_child_and_leaves_caller_usable(self):
        with transaction.atomic():
            locked_child = Kinder.objects.select_for_update().get(pk=self.child.id)
            plan = self.plan_locked_child_number(child=locked_child, number=7)
            Kinder.objects.create(
                kid_index="KID-EDIT-HELPER-DUPLICATE",
                kid_vorname="Grace",
                kid_nachname="Hopper",
                turnus=self.turnus,
                happy_cleaning_number=7,
            )
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.apply_locked_child_number(child=locked_child, plan=plan)

            in_memory_state = (
                locked_child.happy_cleaning_number,
                locked_child.happy_cleaning_number_version,
            )
            database_state = Kinder.objects.filter(pk=self.child.id).values_list(
                "happy_cleaning_number",
                "happy_cleaning_number_version",
            ).get()
            self.actor.profil.rufname = "Outer transaction remained usable"
            self.actor.profil.save(update_fields=("rufname",))

        self.actor.profil.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(database_state, (9, 1))
        self.assertEqual(self.actor.profil.rufname, "Outer transaction remained usable")
        self.assertEqual(in_memory_state, (9, 1))
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_locked_helper_changes_roll_back_with_its_caller(self):
        with self.assertRaisesRegex(RuntimeError, "caller rejected aggregate"):
            with transaction.atomic():
                locked_child = Kinder.objects.select_for_update().get(pk=self.child.id)
                plan = self.plan_locked_child_number(child=locked_child, number=7)
                self.apply_locked_child_number(child=locked_child, plan=plan)
                raise RuntimeError("caller rejected aggregate")

        self.child.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        self.assertEqual(self.child.happy_cleaning_number_version, 1)
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(HappyCleaningCommandRequest.objects.exists())
        self.assertEqual(self.published, [])

    def test_standalone_number_command_remains_the_side_effect_owner(self):
        context = CommandContext(
            turnus=self.turnus,
            actor_id=self.actor.id,
            actor_label="Helper Actor",
            request_id="standalone-number-control",
            client_ip=None,
            user_agent="helper-test",
        )

        response, replayed = set_child_number(
            context,
            self.child.id,
            7,
            expected_version=1,
        )

        self.child.refresh_from_db()
        self.event.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(response["child"]["number"], 7)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assertEqual(self.event.revision, 5)
        self.assertEqual(
            AuditEvent.objects.filter(request_id=context.request_id).count(),
            1,
        )
        self.assertEqual(
            HappyCleaningCommandRequest.objects.filter(
                request_id=context.request_id,
            ).count(),
            1,
        )
        self.assertEqual(
            self.published,
            [
                {
                    "kind": "child_number",
                    "happy_cleaning_id": self.event.id,
                    "revision": 5,
                    "request_id": context.request_id,
                }
            ],
        )
