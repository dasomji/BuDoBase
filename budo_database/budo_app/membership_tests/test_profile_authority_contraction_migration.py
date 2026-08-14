from datetime import date

from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from budo_app.happy_cleaning_tests.migration_fixtures import restore_latest_migration_state


class ProfileAuthorityContractionMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0095_harden_membership_selection_activation")
    reconcile_to = ("budo_app", "0096_contract_legacy_profile_authority")
    migrate_to = ("budo_app", "0097_remove_legacy_profile_authority")

    def test_only_unactivated_legacy_profiles_are_reconciled(self):
        executor = MigrationExecutor(connection)
        self.assertTrue(executor.loader.get_migration(*self.reconcile_to).atomic)
        self.assertTrue(executor.loader.get_migration(*self.migrate_to).atomic)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        User = apps.get_model("auth", "User")
        Profil = apps.get_model("budo_app", "Profil")
        Turnus = apps.get_model("budo_app", "Turnus")
        Membership = apps.get_model("budo_app", "TurnusMembership")

        legacy = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        selected = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 8, 1))

        activated = User.objects.create(username="activated")
        activated_profile = Profil.objects.create(
            user_id=activated.id, turnus_id=legacy.id, rolle="o",
            selected_turnus_id=selected.id, membership_selection_enabled=True,
        )
        Membership.objects.create(
            user_id=activated.id,
            turnus_id=legacy.id,
            functional_role="teamer",
            team_label="Legacy custom label",
        )
        Membership.objects.create(
            user_id=activated.id,
            turnus_id=selected.id,
            functional_role="leitung",
            team_label="Selected custom label",
        )

        unactivated = User.objects.create(username="unactivated")
        unactivated_profile = Profil.objects.create(
            user_id=unactivated.id, turnus_id=legacy.id, rolle="k",
            membership_selection_enabled=False,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.reconcile_to])
        reconciled = executor.loader.project_state([self.reconcile_to]).apps
        ReconciledProfile = reconciled.get_model("budo_app", "Profil")
        ReconciledMembership = reconciled.get_model("budo_app", "TurnusMembership")

        self.assertEqual(
            ReconciledProfile.objects.get(user_id=unactivated.id).selected_turnus_id,
            legacy.id,
        )
        self.assertEqual(
            ReconciledMembership.objects.get(
                user_id=unactivated.id, turnus_id=legacy.id
            ).team_label,
            "Küche",
        )
        self.assertIn(
            "membership_selection_enabled",
            {field.name for field in ReconciledProfile._meta.fields},
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        MigratedProfile = migrated.get_model("budo_app", "Profil")
        MigratedMembership = migrated.get_model("budo_app", "TurnusMembership")

        self.assertEqual(
            MigratedProfile.objects.get(user_id=activated.id).selected_turnus_id,
            selected.id,
        )
        self.assertEqual(
            list(MigratedMembership.objects.filter(user_id=activated.id).order_by("turnus_id").values_list("turnus_id", "functional_role", "team_label")),
            [
                (legacy.id, "teamer", "Legacy custom label"),
                (selected.id, "leitung", "Selected custom label"),
            ],
        )
        self.assertEqual(
            MigratedProfile.objects.get(user_id=unactivated.id).selected_turnus_id,
            legacy.id,
        )
        self.assertEqual(
            MigratedMembership.objects.get(user_id=unactivated.id, turnus_id=legacy.id).team_label,
            "Küche",
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.reconcile_to])
        reversed_apps = executor.loader.project_state([self.reconcile_to]).apps
        ReversedProfile = reversed_apps.get_model("budo_app", "Profil")
        self.assertIn(
            "membership_selection_enabled",
            {field.name for field in ReversedProfile._meta.fields},
        )
        reversed_profile = ReversedProfile.objects.get(user_id=unactivated.id)
        self.assertFalse(reversed_profile.membership_selection_enabled)
        reversed_profile.membership_selection_enabled = True
        reversed_profile.save(update_fields=("membership_selection_enabled",))
        reversed_profile.membership_selection_enabled = False
        with self.assertRaises(DatabaseError), transaction.atomic():
            reversed_profile.save(update_fields=("membership_selection_enabled",))

        # Reapplying the atomic schema contraction proves the 0097 reverse leaves
        # the trigger and columns in a state that can be resumed safely.
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
