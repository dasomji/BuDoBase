from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.models import AuditEvent, Turnus, TurnusMembership


class AdminTeamManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.test", "pw")
        self.member = User.objects.create_user("alex", first_name="Alex", last_name="Muster")
        self.turnus = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 7, 4))
        self.membership = TurnusMembership.objects.create(user=self.member, turnus=self.turnus, team_label="Küche")

    def test_overview_groups_members_and_exposes_role_and_label(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("route-data-api", kwargs={"contract_key": "admin-team-overview"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["years"][0]["year"], 2026)
        self.assertEqual(response.json()["years"][0]["turnuses"][0]["members"][0]["team_label"], "Küche")

    def test_only_superuser_can_change_leitung_and_change_is_audited(self):
        url = reverse("admin-membership-role-api", args=(self.membership.pk,))
        staff = User.objects.create_user("staff", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post(url, {"functional_role": "leitung"}).status_code, 403)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.functional_role, "teamer")

        self.client.force_login(self.admin)
        response = self.client.post(url, {"functional_role": "leitung"})
        self.assertEqual(response.status_code, 200)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.functional_role, "leitung")
        self.assertTrue(AuditEvent.objects.filter(action="membership.role.change", turnus=self.turnus).exists())

    def test_role_mutation_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(reverse("admin-membership-role-api", args=(self.membership.pk,)), {"functional_role": "leitung"})
        self.assertEqual(response.status_code, 403)
