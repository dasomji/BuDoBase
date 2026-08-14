from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import BetreuerinnenGeld, Kinder, Schwerpunkte, Turnus
from budo_app.read_contract_tests.fixtures import ActiveTurnusFixtureFactory
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
)


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


class ProfileContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(
            username="profile-user",
            email="ada@example.test",
            password="secret",
        )
        self.profile = self.user.profil
        self.profile.rufname = "Ada"
        self.profile.telefonnummer = "+4312345"
        self.profile.allergien = "Haselnüsse"
        self.profile.coffee = "Schwarz"
        self.profile.rolle = "o"
        self.profile.essen = "vt"
        self.profile.budo_family = "M"
        self.profile.turnus = self.turnus
        self.profile.save()
        create_membership(user=self.user, turnus=self.turnus, team_label="Organisator")
        select_turnus(self.user, self.turnus)
        self.focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w1"),
        )
        self.focus.betreuende.add(self.profile)
        BetreuerinnenGeld.objects.create(
            who=self.profile,
            amount=12.5,
            what="Deprecated accounting data",
        )
        Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Privates",
            kid_nachname="Kind",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
        )
        self.client.force_login(self.user)

    def contract_url(self, key, profile=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={profile.id}" if profile else url

    def create_teammate(self, *, username="selected-team-card", name="Grace"):
        selected_user = User.objects.create_user(
            username=username,
            email="grace@example.test",
        )
        selected = selected_user.profil
        selected.rufname = name
        selected.telefonnummer = "+4398765"
        selected.allergien = "Sellerie"
        selected.coffee = "Hafermilch"
        selected.rolle = "b"
        selected.essen = "vn"
        selected.budo_family = "L"
        selected.turnus = self.turnus
        selected.save()
        create_membership(user=selected_user, turnus=self.turnus, team_label="Betreuer:in")
        return selected

    def grant_profile_change(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_profil"),
        )

    def test_profile_returns_only_own_focused_profile_data_without_accounting(self):
        response = self.client.get(self.contract_url("profile"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"profile", "focuses"})
        self.assertEqual(payload["profile"], {
            "id": self.profile.id,
            "email": "ada@example.test",
            "rufname": "Ada",
            "phone": "+4312345",
            "allergies": "Haselnüsse",
            "coffee": "Schwarz",
            "role": "teamer",
            "role_display": "Organisator",
            "food": "vt",
            "food_display": "🧀 Vegetarisch",
            "budo_family": "M",
        })
        self.assertEqual(payload["focuses"], [{
            "id": self.focus.id,
            "name": "Wald",
        }])
        self.assertNotContains(response, "Deprecated accounting data")
        self.assertNotContains(response, "Privates Kind")
        self.assertNotIn("money_total", payload["profile"])
        self.assertNotIn("money_items", payload["profile"])

    def test_only_profile_admins_can_read_a_selected_profile_for_editing(self):
        selected = self.create_teammate()

        denied = self.client.get(self.contract_url("profile", selected))
        self.grant_profile_change()
        allowed = self.client.get(self.contract_url("profile", selected))

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        payload = allowed.json()
        self.assertEqual(payload["profile"]["id"], selected.id)
        self.assertEqual(payload["profile"]["rufname"], "Grace")
        self.assertNotIn("money_total", payload["profile"])

    def test_profile_admin_can_update_a_selected_profile_but_ordinary_users_cannot(self):
        selected = self.create_teammate()
        target = f"/profil/{selected.id}/"
        submission = {
            "_target": target,
            "rufname": "Grace Neu",
            "email": "Grace.Neu@EXAMPLE.TEST",
            "allergien": "Keine",
            "coffee": "Milch",
            "rolle": "o",
            "essen": "vt",
            "telefonnummer": "+436641234567",
            "budo_family": "XL",
            "turnus": self.other_turnus.id,
        }

        denied = self.client.post(reverse("form-submit-api"), submission)
        selected.refresh_from_db()
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(selected.rufname, "Grace")

        self.grant_profile_change()
        saved = self.client.post(reverse("form-submit-api"), submission)

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json(), {"ok": True, "redirect": "/teams/"})
        selected.refresh_from_db()
        selected.user.refresh_from_db()
        self.assertEqual(selected.rufname, "Grace Neu")
        self.assertEqual(selected.user.email, "grace.neu@example.test")
        self.assertEqual(self.user.email, "ada@example.test")
        self.assertEqual(selected.allergien, "Keine")
        self.assertEqual(selected.budo_family, "XL")
        self.assertFalse(selected.user.turnus_memberships.filter(turnus=self.other_turnus).exists())

    def test_deprecated_teamer_accounting_route_and_form_target_are_unavailable(self):
        selected = self.create_teammate()

        page = self.client.get(f"/teamer/{selected.id}/")
        submission = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/teamer/{selected.id}/",
                "amount": "8.50",
                "what": "Einkauf",
            },
        )

        self.assertEqual(page.status_code, 404)
        self.assertEqual(submission.status_code, 400)
        self.assertFalse(selected.betreuerinnen_geld.exists())

    def test_profile_contract_requires_authentication(self):
        self.client.logout()

        profile = self.client.get(self.contract_url("profile"))

        self.assertEqual(profile.status_code, 403)

    def test_profile_submission_cannot_change_membership_role_or_selected_turnus(self):
        submitted = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/bearbeiten/",
                "rufname": "Ada Test",
                "email": "ada@example.test",
                "allergien": "Haselnüsse",
                "coffee": "Schwarz",
                "rolle": "o",
                "essen": "vt",
                "telefonnummer": "+4312345",
                "budo_family": "M",
                "turnus": self.other_turnus.id,
            },
        )

        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json(), {
            "ok": True,
            "redirect": "/dashboard/",
        })
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rufname, "Ada Test")
        self.assertEqual(self.profile.selected_turnus, self.turnus)
        membership = self.user.turnus_memberships.get(turnus=self.turnus)
        self.assertEqual(membership.team_label, "Organisator")

    def test_profile_form_preserves_validation_persistence_redirect_and_message(self):
        invalid = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/bearbeiten/",
                "rufname": "Not saved",
                "email": "ada@example.test",
                "allergien": "Neu",
                "coffee": "Milch",
                "rolle": "b",
                "essen": "vn",
                "telefonnummer": "not-a-phone",
                "budo_family": "L",
                "turnus": self.turnus.id,
            },
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertFalse(invalid.json()["ok"])
        self.assertTrue(invalid.json()["errors"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rufname, "Ada")

        saved = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/bearbeiten/",
                "rufname": "Ada Neu",
                "email": "  Ada.Neu@EXAMPLE.TEST  ",
                "allergien": "Keine",
                "coffee": "Milch",
                "rolle": "b",
                "essen": "vn",
                "telefonnummer": "+436641234567",
                "budo_family": "XL",
                "turnus": self.other_turnus.id,
            },
        )

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json(), {
            "ok": True,
            "redirect": "/dashboard/",
        })
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rufname, "Ada Neu")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada.neu@example.test")
        self.assertEqual(self.profile.allergien, "Keine")
        self.assertEqual(self.profile.coffee, "Milch")
        self.assertEqual(self.profile.essen, "vn")
        self.assertEqual(self.profile.budo_family, "XL")
        self.assertEqual(str(self.profile.telefonnummer), "+436641234567")
        profile_contract = self.client.get(self.contract_url("profile")).json()
        self.assertEqual(profile_contract["profile"]["email"], "ada.neu@example.test")
        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertEqual(bootstrap["profile"]["rufname"], "Ada Neu")
        self.assertEqual(bootstrap["turnus"]["id"], self.turnus.id)
        self.assertEqual(bootstrap["messages"], [{
            "text": "Profil upgedatet!",
            "tags": "success",
        }])

    def test_profile_email_is_required_valid_unique_and_does_not_partially_save(self):
        User.objects.create_user(
            username="email-owner",
            email="taken@example.test",
        )
        submission = {
            "_target": "/profil/bearbeiten/",
            "rufname": "Must not be saved",
            "allergien": "Neu",
            "coffee": "Milch",
            "essen": "vn",
            "telefonnummer": "+436641234567",
            "budo_family": "L",
        }

        for email in ("", "not-an-email", "TAKEN@EXAMPLE.TEST"):
            with self.subTest(email=email):
                rejected = self.client.post(
                    reverse("form-submit-api"),
                    {**submission, "email": email},
                )

                self.assertEqual(rejected.status_code, 422)
                self.assertFalse(rejected.json()["ok"])
                self.assertTrue(rejected.json()["errors"])
                self.profile.refresh_from_db()
                self.user.refresh_from_db()
                self.assertEqual(self.profile.rufname, "Ada")
                self.assertEqual(self.user.email, "ada@example.test")


@override_settings(STORAGES=TEST_STORAGES)
class ProfileContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="profile-performance")
        approve_and_select_turnus(self.user.profil.user, self.turnus)
        self.user.profil.save()
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contract(self, key):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return measure_http_get(self.client, url)

    def test_profile_queries_stay_bounded_and_payload_beats_legacy(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = self.measure_contract("profile")

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        focuses = list(
            Schwerpunkte.objects.filter(schwerpunktzeit__turnus=self.turnus),
        )
        self.user.profil.swp.add(*focuses)
        realistic = self.measure_contract("profile")

        self.assertEqual(realistic.status_code, 200)
        self.assertQueryCountAtMost(realistic, 9)
        self.assertQueryGrowthAtMost(small, realistic, 1)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
