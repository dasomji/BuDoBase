from importlib import import_module
from unittest.mock import Mock

from django.test import SimpleTestCase

migration = import_module(
    "budo_app.migrations.0095_harden_membership_selection_activation"
)


class MembershipHardeningMigrationSqlTests(SimpleTestCase):
    def test_postgresql_reverse_drops_trigger_from_profile_table(self):
        apps = Mock()
        apps.get_model.return_value._meta.db_table = "budo_app_profil"
        editor = Mock()
        editor.connection.vendor = "postgresql"

        migration.remove_monotonic_activation(apps, editor)

        self.assertEqual(
            editor.execute.call_args_list[0].args[0],
            "DROP TRIGGER IF EXISTS budo_profile_activation_monotonic ON budo_app_profil",
        )

    def test_unknown_vendor_fails_loudly_instead_of_omitting_invariant(self):
        apps = Mock()
        editor = Mock()
        editor.connection.vendor = "mysql"

        with self.assertRaisesRegex(RuntimeError, "supports only PostgreSQL and SQLite"):
            migration.install_monotonic_activation(apps, editor)
        with self.assertRaisesRegex(RuntimeError, "cannot reverse safely"):
            migration.remove_monotonic_activation(apps, editor)

        editor.execute.assert_not_called()
