from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.models import Turnus, TurnusMembership


User = get_user_model()


class ExcelUploadAuthorizationTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.foreign_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.url = reverse("upload_excel", args=(self.turnus.pk,))

    def user(self, name, *, role=None, superuser=False):
        user = User.objects.create_user(name, password="testpass123")
        if superuser:
            user.is_superuser = True
            user.save(update_fields=("is_superuser",))
        if role is not None:
            TurnusMembership.objects.create(
                user=user,
                turnus=self.turnus,
                functional_role=role,
            )
        return user

    def test_only_product_admin_can_open_global_import_configuration(self):
        ordinary = self.user("ordinary")
        self.client.force_login(ordinary)
        self.assertEqual(self.client.get(reverse("uploadFile")).status_code, 403)

        admin = self.user("admin", superuser=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("uploadFile")).status_code, 200)

    def test_existing_import_is_scoped_to_admin_or_relevant_leitung(self):
        denied_users = (
            self.user("no-membership"),
            self.user("teamer", role=TurnusMembership.FunctionalRole.TEAMER),
        )
        foreign_leitung = self.user("foreign-leitung")
        TurnusMembership.objects.create(
            user=foreign_leitung,
            turnus=self.foreign_turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        for user in (*denied_users, foreign_leitung):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 404)

        leitung = self.user(
            "leitung", role=TurnusMembership.FunctionalRole.LEITUNG
        )
        self.client.force_login(leitung)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        admin = self.user("global-admin", superuser=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_unauthorized_and_missing_import_targets_are_indistinguishable(self):
        user = self.user("unscoped")
        self.client.force_login(user)
        missing = reverse("upload_excel", args=(999999,))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get(missing).status_code, 404)

    def test_import_mutation_requires_csrf(self):
        leitung = self.user(
            "csrf-leitung", role=TurnusMembership.FunctionalRole.LEITUNG
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(leitung)
        self.assertEqual(client.post(self.url, {}).status_code, 403)
