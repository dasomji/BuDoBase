from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from budo_app.happy_cleaning_tests.migration_fixtures import (
    restore_latest_migration_state,
)


class TurnusMembershipExpandMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0089_alter_tag_icon")
    migrate_to = ("budo_app", "0090_turnus_memberships")

    def test_existing_profile_assignment_becomes_membership_and_selection(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        User = old_apps.get_model("auth", "User")
        Profil = old_apps.get_model("budo_app", "Profil")
        Turnus = old_apps.get_model("budo_app", "Turnus")
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 4),
        )
        user = User.objects.create(username="existing-teamer")
        profile = Profil.objects.create(user=user, rolle="k", turnus=turnus)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        Membership = migrated.get_model("budo_app", "TurnusMembership")
        MigratedProfil = migrated.get_model("budo_app", "Profil")

        membership = Membership.objects.get(user_id=user.pk, turnus_id=turnus.pk)
        self.assertEqual(
            (
                membership.functional_role,
                membership.team_label,
                MigratedProfil.objects.get(pk=profile.pk).selected_turnus_id,
            ),
            ("teamer", "k", turnus.pk),
        )

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
