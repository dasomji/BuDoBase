from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from budo_app.models import AuditEvent, Turnus, TurnusMembership


class LeitungTeamManagementHttpTests(TestCase):
    def test_leitung_can_add_an_available_account_as_teamer_to_own_turnus(self):
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2027, 7, 10),
        )
        leitung = User.objects.create_user("leitung")
        available = User.objects.create_user(
            "alex",
            first_name="Alex",
            last_name="Muster",
        )
        TurnusMembership.objects.create(
            user=leitung,
            turnus=turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        self.client.force_login(leitung)

        response = self.client.post(
            f"/api/turnusse/{turnus.id}/memberships/",
            {"user_id": available.id},
        )

        self.assertEqual(response.status_code, 201)
        workspace = self.client.get(
            reverse("route-data-api", args=("team-management",))
        )
        self.assertEqual(workspace.status_code, 200)
        managed_turnus = workspace.json()["years"][0]["turnuses"][0]
        self.assertEqual(
            managed_turnus["members"],
            [
                {
                    "id": managed_turnus["members"][0]["id"],
                    "user_id": leitung.id,
                    "name": "leitung",
                    "functional_role": "leitung",
                    "role_label": "Leitung",
                    "team_label": "",
                },
                {
                    "id": response.json()["membership_id"],
                    "user_id": available.id,
                    "name": "Alex Muster",
                    "functional_role": "teamer",
                    "role_label": "Teamer",
                    "team_label": "",
                },
            ],
        )

    def setUp(self):
        self.own = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2028, 7, 1))
        self.foreign = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2028, 7, 15))
        self.leitung = User.objects.create_user("own-leitung")
        self.member = User.objects.create_user("member", first_name="Mara", last_name="Muster")
        self.leadership = TurnusMembership.objects.create(
            user=self.leitung, turnus=self.own, functional_role="leitung",
        )
        self.membership = TurnusMembership.objects.create(user=self.member, turnus=self.own)
        self.client.force_login(self.leitung)

    def test_directory_exposes_accounts_but_not_foreign_membership_data(self):
        foreign_user = User.objects.create_user("foreign-person")
        TurnusMembership.objects.create(user=foreign_user, turnus=self.foreign, team_label="Secret")
        payload = self.client.get(reverse("route-data-api", args=("team-management",))).json()
        person = next(item for item in payload["people"] if item["id"] == foreign_user.id)
        self.assertEqual(person["relationships"], [])
        self.assertEqual(person["turnus_ids"], [])
        self.assertNotIn("Secret", str(payload))

    def test_cross_turnus_targets_are_indistinguishable_and_role_cannot_be_forged(self):
        foreign_member = TurnusMembership.objects.create(user=self.member, turnus=self.foreign)
        missing = foreign_member.id + 9999
        for membership_id in (foreign_member.id, missing):
            self.assertEqual(self.client.post(
                reverse("membership-label-api", args=(membership_id,)), {"team_label": "Leitung"},
            ).status_code, 404)
            self.assertEqual(self.client.post(
                reverse("membership-remove-api", args=(membership_id,)), {},
            ).status_code, 404)
        target = User.objects.create_user("target")
        responses = [
            self.client.post(
                reverse("teamer-membership-create-api", args=(turnus_id,)),
                {"user_id": target.id, "functional_role": "leitung"},
            )
            for turnus_id in (self.foreign.id, self.foreign.id + 9999)
        ]
        self.assertEqual([response.status_code for response in responses], [404, 404])
        self.assertEqual(responses[0].content, responses[1].content)
        self.assertFalse(TurnusMembership.objects.filter(user=target).exists())
        self.assertFalse(AuditEvent.objects.filter(action="membership.create").exists())

    def test_label_is_membership_specific_non_authority_and_audited(self):
        other = TurnusMembership.objects.create(user=self.member, turnus=self.foreign, team_label="Küche")
        response = self.client.post(
            reverse("membership-label-api", args=(self.membership.id,)),
            {"team_label": "Leitung"},
        )
        self.assertEqual(response.status_code, 200)
        self.membership.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.membership.team_label, "Leitung")
        self.assertEqual(self.membership.functional_role, "teamer")
        self.assertEqual(other.team_label, "Küche")
        self.assertTrue(AuditEvent.objects.filter(action="membership.label.change").exists())

    def test_invalid_label_returns_a_field_addressable_400(self):
        response = self.client.post(
            reverse("membership-label-api", args=(self.membership.id,)),
            {"team_label": "x" * 256},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(response.json()), ["team_label"])
        self.assertTrue(response.json()["team_label"])
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.team_label, "")

    def test_remove_immediately_repairs_selection_and_is_audited(self):
        fallback = Turnus.objects.create(turnus_nr=3, turnus_beginn=date(2028, 8, 1))
        TurnusMembership.objects.create(user=self.member, turnus=fallback)
        profile = self.member.profil
        profile.selected_turnus = self.own
        profile.save()
        response = self.client.post(reverse("membership-remove-api", args=(self.membership.id,)), {})
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.selected_turnus_id, fallback.id)
        self.assertFalse(TurnusMembership.objects.filter(pk=self.membership.id).exists())
        self.assertTrue(AuditEvent.objects.filter(action="membership.remove").exists())

    def test_mutations_require_csrf_and_audit_failure_rolls_back(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.leitung)
        self.assertEqual(csrf_client.post(
            reverse("membership-label-api", args=(self.membership.id,)), {"team_label": "Küche"},
        ).status_code, 403)
        with patch("budo_app.team_membership_views.record_audit_event", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("membership-remove-api", args=(self.membership.id,)), {})
        self.assertTrue(TurnusMembership.objects.filter(pk=self.membership.id).exists())
