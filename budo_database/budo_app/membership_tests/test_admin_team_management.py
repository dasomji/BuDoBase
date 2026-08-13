from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.models import AuditEvent, Turnus, TurnusJoinRequest, TurnusMembership
from budo_app.memberships import update_membership


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

    def test_overview_includes_real_pending_requests_and_users_without_membership(self):
        requester = User.objects.create_user("bea", first_name="Bea", last_name="Beispiel")
        available = User.objects.create_user("chris", first_name="Chris", last_name="Frei")
        TurnusJoinRequest.objects.create(user=requester, turnus=self.turnus)
        TurnusJoinRequest.objects.create(
            user=available,
            turnus=self.turnus,
            status=TurnusJoinRequest.Status.REJECTED,
        )
        self.client.force_login(self.admin)

        payload = self.client.get(reverse("route-data-api", kwargs={"contract_key": "admin-team-overview"})).json()

        turnus = payload["years"][0]["turnuses"][0]
        self.assertEqual(turnus["request_summary"], {"pending": 1})
        self.assertEqual(turnus["pending_requests"][0]["name"], "Bea Beispiel")
        person = next(person for person in payload["people"] if person["id"] == available.id)
        self.assertEqual(person["relationships"], [])
        self.assertTrue(person["available"])

    def test_product_admin_page_is_reachable_ahead_of_django_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin-team-overview-page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)

    @patch("budo_app.admin_team_views.update_membership", wraps=update_membership)
    def test_only_superuser_can_change_leitung_through_domain_seam_and_change_is_audited(self, update):
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
        update.assert_called_once()
        self.assertEqual(update.call_args.kwargs["functional_role"], "leitung")
        self.assertTrue(AuditEvent.objects.filter(action="membership.role.change", turnus=self.turnus).exists())

    def test_role_mutation_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(reverse("admin-membership-role-api", args=(self.membership.pk,)), {"functional_role": "leitung"})
        self.assertEqual(response.status_code, 403)

    def test_forged_role_returns_stable_400_without_changing_membership(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-membership-role-api", args=(self.membership.pk,)),
            {"functional_role": "owner"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"functional_role": "Ungültige Funktionsrolle."})
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.functional_role, "teamer")
        self.assertFalse(AuditEvent.objects.filter(action="membership.role.change").exists())

    def test_nonexistent_membership_returns_404(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-membership-role-api", args=(self.membership.pk + 1000,)),
            {"functional_role": "leitung"},
        )
        self.assertEqual(response.status_code, 404)

    def test_setting_existing_role_is_an_unaudited_noop(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-membership-role-api", args=(self.membership.pk,)),
            {"functional_role": "teamer"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "membership_id": self.membership.pk,
            "functional_role": "teamer",
            "changed": False,
        })
        self.assertFalse(AuditEvent.objects.filter(action="membership.role.change").exists())
