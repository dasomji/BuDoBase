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
        expected_labels = {
            "b": "Betreuer:in",
            "k": "Küche",
            "o": "Organisator",
            "f": "Freiwillige:r",
            "": "",
        }
        profiles = []
        for role_code in expected_labels:
            user = User.objects.create(username=f"existing-{role_code or 'blank'}")
            profiles.append(
                Profil.objects.create(user=user, rolle=role_code, turnus=turnus)
            )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        Membership = migrated.get_model("budo_app", "TurnusMembership")
        MigratedProfil = migrated.get_model("budo_app", "Profil")

        for profile in profiles:
            membership = Membership.objects.get(
                user_id=profile.user_id, turnus_id=turnus.pk
            )
            self.assertEqual(membership.functional_role, "teamer")
            self.assertEqual(membership.team_label, expected_labels[profile.rolle])
            self.assertEqual(
                MigratedProfil.objects.get(pk=profile.pk).selected_turnus_id,
                turnus.pk,
            )

        # This is an expand migration: reversal drops only the new projection.
        # The untouched legacy fields remain the rollback source of truth.
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        rolled_back = executor.loader.project_state([self.migrate_from]).apps
        RolledBackProfil = rolled_back.get_model("budo_app", "Profil")
        for profile in profiles:
            restored = RolledBackProfil.objects.get(pk=profile.pk)
            self.assertEqual(restored.rolle, profile.rolle)
            self.assertEqual(restored.turnus_id, turnus.pk)

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
