from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from budo_app.happy_cleaning_tests.migration_fixtures import (
    restore_latest_migration_state,
)


class MembershipSelectionActivationMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0092_turnus_join_request_notifications")
    migrate_to = ("budo_app", "0093_profil_membership_selection_enabled")

    def test_only_existing_membership_profiles_are_activated(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        User = old_apps.get_model("auth", "User")
        Profil = old_apps.get_model("budo_app", "Profil")
        Turnus = old_apps.get_model("budo_app", "Turnus")
        Membership = old_apps.get_model("budo_app", "TurnusMembership")

        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2027, 7, 10),
        )
        member = User.objects.create(username="member")
        legacy = User.objects.create(username="legacy")
        Profil.objects.create(user=member, turnus=turnus)
        Profil.objects.create(user=legacy, turnus=turnus)
        Membership.objects.create(user=member, turnus=turnus)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        MigratedProfil = migrated.get_model("budo_app", "Profil")

        self.assertTrue(
            MigratedProfil.objects.get(user_id=member.pk).membership_selection_enabled
        )
        self.assertFalse(
            MigratedProfil.objects.get(user_id=legacy.pk).membership_selection_enabled
        )

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
