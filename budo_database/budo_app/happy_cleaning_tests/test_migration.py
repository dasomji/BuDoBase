from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HappyCleaningMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0070_auditevent")
    migrate_to = ("budo_app", "0071_happy_cleaning_schema")
    restore_to = ("budo_app", "0072_happycleaningcommandrequest")

    def test_existing_children_keep_a_null_happy_cleaning_number(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Turnus = old_apps.get_model("budo_app", "Turnus")
        Kinder = old_apps.get_model("budo_app", "Kinder")
        turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        child = Kinder.objects.create(
            kid_index="PRE-0071",
            kid_vorname="Existing",
            kid_nachname="Child",
            turnus=turnus,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        MigratedKinder = new_apps.get_model("budo_app", "Kinder")

        self.assertIsNone(
            MigratedKinder.objects.get(pk=child.pk).happy_cleaning_number
        )

    def tearDown(self):
        MigrationExecutor(connection).migrate([self.restore_to])
        super().tearDown()
