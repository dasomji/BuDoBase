from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from budo_app.happy_cleaning_tests.migration_fixtures import (
    restore_latest_migration_state,
)


class KidEditFoundationMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0082_allow_zero_happy_cleaning_station_capacity")
    migrate_to = ("budo_app", "0083_kid_edit_foundation")

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Turnus = old_apps.get_model("budo_app", "Turnus")
        Kinder = old_apps.get_model("budo_app", "Kinder")
        CommandRequest = old_apps.get_model(
            "budo_app",
            "HappyCleaningCommandRequest",
        )

        self.turnus = Turnus.objects.create(
            turnus_nr=161,
            turnus_beginn=date(2026, 7, 1),
        )
        self.child = Kinder.objects.create(
            kid_index="PRE-161-01",
            kid_vorname="Existing",
            kid_nachname="Child",
            turnus=self.turnus,
        )
        self.command_request = CommandRequest.objects.create(
            turnus=self.turnus,
            actor_id=42,
            request_id="pre-161-01-request",
            action="happy_cleaning.child_number.change",
            response={"ok": True, "result": "updated"},
        )

    def migrate_to_foundation(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        return executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserves_rows_and_backfills_compatible_defaults(self):
        apps = self.migrate_to_foundation()
        Kinder = apps.get_model("budo_app", "Kinder")
        CommandRequest = apps.get_model(
            "budo_app",
            "HappyCleaningCommandRequest",
        )

        migrated_child = Kinder.objects.get(pk=self.child.pk)
        migrated_request = CommandRequest.objects.get(pk=self.command_request.pk)

        self.assertEqual(migrated_child.edit_version, 1)
        self.assertEqual(migrated_child.kid_index, "PRE-161-01")
        self.assertEqual(migrated_child.kid_vorname, "Existing")
        self.assertEqual(migrated_child.kid_nachname, "Child")
        self.assertEqual(migrated_child.turnus_id, self.turnus.pk)
        self.assertEqual(migrated_request.turnus_id, self.turnus.pk)
        self.assertEqual(migrated_request.actor_id, 42)
        self.assertEqual(migrated_request.request_id, "pre-161-01-request")
        self.assertEqual(
            migrated_request.action,
            "happy_cleaning.child_number.change",
        )
        self.assertEqual(
            migrated_request.response,
            {"ok": True, "result": "updated"},
        )
        self.assertIsNone(migrated_request.fingerprint)
        self.assertEqual(migrated_request.status_code, 200)

    def test_new_rows_use_the_foundation_defaults_and_database_constraints(self):
        apps = self.migrate_to_foundation()
        Kinder = apps.get_model("budo_app", "Kinder")
        CommandRequest = apps.get_model(
            "budo_app",
            "HappyCleaningCommandRequest",
        )

        edit_version_field = Kinder._meta.get_field("edit_version")
        fingerprint_field = CommandRequest._meta.get_field("fingerprint")
        status_code_field = CommandRequest._meta.get_field("status_code")
        self.assertEqual(edit_version_field.default, 1)
        self.assertEqual(fingerprint_field.max_length, 80)
        self.assertTrue(fingerprint_field.null)
        self.assertEqual(
            status_code_field.get_internal_type(),
            "PositiveSmallIntegerField",
        )
        self.assertEqual(status_code_field.default, 200)

        new_child = Kinder.objects.create(
            kid_index="POST-161-01",
            kid_vorname="New",
            kid_nachname="Child",
            turnus_id=self.turnus.pk,
        )
        self.assertEqual(new_child.edit_version, 1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Kinder.objects.create(
                kid_index="POST-161-01-ZERO",
                kid_vorname="Invalid",
                kid_nachname="Version",
                turnus_id=self.turnus.pk,
                edit_version=0,
            )

        legacy_request = CommandRequest.objects.create(
            turnus_id=self.turnus.pk,
            actor_id=43,
            request_id="legacy-null-fingerprint",
            action="happy_cleaning.child_number.change",
            response={"ok": True},
        )
        self.assertIsNone(legacy_request.fingerprint)
        self.assertEqual(legacy_request.status_code, 200)

        with self.assertRaises(IntegrityError), transaction.atomic():
            CommandRequest.objects.create(
                turnus_id=self.turnus.pk,
                actor_id=44,
                request_id="kid-edit-null-fingerprint",
                action="kid.edit",
                response={"ok": True},
            )

        kid_edit_request = CommandRequest.objects.create(
            turnus_id=self.turnus.pk,
            actor_id=45,
            request_id="kid-edit-with-fingerprint",
            action="kid.edit",
            fingerprint="opaque-fingerprint",
            response={"ok": True},
        )
        persisted_request = CommandRequest.objects.get(pk=kid_edit_request.pk)
        self.assertEqual(persisted_request.fingerprint, "opaque-fingerprint")
        self.assertEqual(persisted_request.status_code, 200)

    def test_backward_preserves_pre_existing_child_and_ledger_history(self):
        apps = self.migrate_to_foundation()
        apps.get_model("budo_app", "Kinder")._meta.get_field("edit_version")
        apps.get_model(
            "budo_app",
            "HappyCleaningCommandRequest",
        )._meta.get_field("fingerprint")

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        rolled_back = executor.loader.project_state([self.migrate_from]).apps
        Kinder = rolled_back.get_model("budo_app", "Kinder")
        CommandRequest = rolled_back.get_model(
            "budo_app",
            "HappyCleaningCommandRequest",
        )

        child = Kinder.objects.get(pk=self.child.pk)
        command_request = CommandRequest.objects.get(pk=self.command_request.pk)
        self.assertEqual(
            (
                child.kid_index,
                child.kid_vorname,
                child.kid_nachname,
                child.turnus_id,
            ),
            ("PRE-161-01", "Existing", "Child", self.turnus.pk),
        )
        self.assertEqual(
            (
                command_request.turnus_id,
                command_request.actor_id,
                command_request.request_id,
                command_request.action,
                command_request.response,
            ),
            (
                self.turnus.pk,
                42,
                "pre-161-01-request",
                "happy_cleaning.child_number.change",
                {"ok": True, "result": "updated"},
            ),
        )

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
