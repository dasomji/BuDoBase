from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from budo_app.models import AuditEvent, Schwerpunkte, Turnus, TurnusMembership


class TeamerTeamManagementReadTests(TestCase):
    def test_teamer_reads_only_own_turnuses_without_management_data(self):
        own = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2028, 7, 1))
        foreign = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2028, 7, 15))
        teamer = User.objects.create_user("teamer", first_name="Tina", last_name="Teamer")
        teammate = User.objects.create_user("teammate", first_name="Mara", last_name="Muster")
        outsider = User.objects.create_user("outsider", first_name="Otto", last_name="Privat")
        teamer.profil.rufname = "Tina Teamer"
        teamer.profil.save(update_fields=("rufname",))
        teammate.profil.rufname = "Mara Muster"
        teammate.profil.save(update_fields=("rufname",))
        TurnusMembership.objects.create(user=teamer, turnus=own)
        TurnusMembership.objects.create(user=teammate, turnus=own)
        TurnusMembership.objects.create(user=teammate, turnus=foreign)
        TurnusMembership.objects.create(user=outsider, turnus=foreign)
        self.client.force_login(teamer)

        response = self.client.get(reverse("route-data-api", args=("team-management",)))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [turnus["id"] for year in payload["years"] for turnus in year["turnuses"]],
            [own.id],
        )
        visible_turnus = payload["years"][0]["turnuses"][0]
        self.assertEqual(
            [member["name"] for member in visible_turnus["members"]],
            ["Mara Muster", "Tina Teamer"],
        )
        self.assertFalse(visible_turnus["can_manage_memberships"])
        self.assertFalse(visible_turnus["can_edit_profiles"])
        self.assertFalse(visible_turnus["excel_uploaded"])
        self.assertFalse(payload["can_create_turnus"])
        teammate_payload = next(
            member for member in visible_turnus["members"] if member["name"] == "Mara Muster"
        )
        self.assertEqual(teammate_payload["profile"]["turnuses"], [str(own)])
        self.assertEqual(visible_turnus["pending_requests"], [])
        self.assertEqual(payload["people"], [])
        self.assertNotContains(response, "Otto Privat")
        denied = self.client.post(
            reverse("turnus-create-api"),
            {"turnus_nr": 3, "turnus_beginn": "2029-07-07"},
        )
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(Turnus.objects.filter(turnus_nr=3, turnus_beginn=date(2029, 7, 7)).exists())

    def test_team_management_embeds_the_existing_profile_card_fields(self):
        turnus = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2028, 7, 1))
        viewer = User.objects.create_user("viewer")
        teammate = User.objects.create_user(
            "teammate",
            email="mara@example.test",
            first_name="Mara",
            last_name="Muster",
        )
        TurnusMembership.objects.create(user=viewer, turnus=turnus)
        membership = TurnusMembership.objects.create(
            user=teammate,
            turnus=turnus,
            team_label="Küche",
        )
        profile = teammate.profil
        profile.rufname = "Mara"
        profile.telefonnummer = "+436641234567"
        profile.allergien = "Nüsse"
        profile.coffee = "Schwarz"
        profile.essen = "vt"
        profile.budo_family = "M"
        profile.save()
        focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=turnus.schwerpunktzeit_set.get(woche="w1"),
        )
        focus.betreuende.add(profile)
        self.client.force_login(viewer)

        payload = self.client.get(
            reverse("route-data-api", args=("team-management",))
        ).json()

        member = next(
            item
            for item in payload["years"][0]["turnuses"][0]["members"]
            if item["id"] == membership.id
        )
        self.assertEqual(member["profile"], {
            "id": profile.id,
            "email": "mara@example.test",
            "rufname": "Mara",
            "phone": "+436641234567",
            "allergies": "Nüsse",
            "coffee": "Schwarz",
            "role": "teamer",
            "role_display": "Küche",
            "food": "vt",
            "food_display": "🧀 Vegetarisch",
            "budo_family": "M",
            "turnuses": [str(turnus)],
            "focuses": [{"id": focus.id, "name": "Wald"}],
        })


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
        leitung.profil.rufname = "leitung"
        leitung.profil.save(update_fields=("rufname",))
        available.profil.rufname = "Alex Muster"
        available.profil.save(update_fields=("rufname",))
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
        membership_fields = (
            "id", "user_id", "name", "functional_role", "role_label", "team_label",
        )
        self.assertEqual(
            [
                {key: member[key] for key in membership_fields}
                for member in managed_turnus["members"]
            ],
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
        self.leitung = User.objects.create_user(
            "own-leitung", email="leitung@example.test",
        )
        self.member = User.objects.create_user(
            "member",
            email="mara@example.test",
            first_name="Mara",
            last_name="Muster",
        )
        self.leadership = TurnusMembership.objects.create(
            user=self.leitung, turnus=self.own, functional_role="leitung",
        )
        self.membership = TurnusMembership.objects.create(user=self.member, turnus=self.own)
        self.client.force_login(self.leitung)

    def test_leitung_creates_a_turnus_and_is_automatically_assigned_as_leitung(self):
        response = self.client.post(
            reverse("turnus-create-api"),
            {"turnus_nr": 3, "turnus_beginn": "2029-07-07"},
        )

        self.assertEqual(response.status_code, 201)
        created = Turnus.objects.get(pk=response.json()["id"])
        membership = TurnusMembership.objects.get(user=self.leitung, turnus=created)
        self.assertEqual(membership.functional_role, TurnusMembership.FunctionalRole.LEITUNG)
        self.assertEqual(response.json(), {
            "id": created.id,
            "label": "T3-2029",
            "number": 3,
            "start": "2029-07-07",
            "end": "2029-07-20",
            "excel_uploaded": False,
        })
        payload = self.client.get(
            reverse("route-data-api", args=("team-management",))
        ).json()
        self.assertTrue(payload["can_create_turnus"])
        self.assertIn(created.id, [
            turnus["id"]
            for year in payload["years"]
            for turnus in year["turnuses"]
        ])

    def test_leitung_can_edit_a_profile_in_own_turnus_but_not_a_foreign_profile(self):
        foreign_member = User.objects.create_user(
            "foreign-member", email="foreign@example.test",
        )
        TurnusMembership.objects.create(user=foreign_member, turnus=self.foreign)
        submission = {
            "rufname": "Mara Neu",
            "email": "Mara.Neu@EXAMPLE.TEST",
            "allergien": "Keine",
            "coffee": "Milch",
            "essen": "vt",
            "telefonnummer": "+436641234567",
            "budo_family": "XL",
        }

        own_response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/profil/{self.member.profil.id}/", **submission},
        )
        foreign_response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/profil/{foreign_member.profil.id}/", **submission},
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.json(), {"ok": True, "redirect": "/teams/"})
        self.assertEqual(foreign_response.status_code, 403)
        self.member.refresh_from_db()
        self.member.profil.refresh_from_db()
        foreign_member.refresh_from_db()
        foreign_member.profil.refresh_from_db()
        self.assertEqual(self.member.profil.rufname, "Mara Neu")
        self.assertEqual(self.member.email, "mara.neu@example.test")
        self.assertNotEqual(foreign_member.profil.rufname, "Mara Neu")
        self.assertEqual(foreign_member.email, "foreign@example.test")

        workspace = self.client.get(
            reverse("route-data-api", args=("team-management",))
        ).json()
        member = next(
            item
            for item in workspace["years"][0]["turnuses"][0]["members"]
            if item["user_id"] == self.member.id
        )
        person = next(
            item for item in workspace["people"] if item["id"] == self.member.id
        )
        self.assertEqual(member["name"], "Mara Neu")
        self.assertEqual(person["name"], "Mara Neu")

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
