from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

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
        self.profile.turnus = self.turnus
        self.profile.save()
        self.focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w1"),
        )
        self.focus.betreuende.add(self.profile)
        self.money = BetreuerinnenGeld.objects.create(
            who=self.profile,
            amount=12.5,
            what="Material",
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

    def test_profile_returns_only_own_focused_profile_data(self):
        response = self.client.get(self.contract_url("profile"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"profile", "focuses", "turnuses"})
        self.assertEqual(payload["profile"], {
            "id": self.profile.id,
            "email": "ada@example.test",
            "rufname": "Ada",
            "phone": "+4312345",
            "allergies": "Haselnüsse",
            "coffee": "Schwarz",
            "role": "o",
            "role_display": "Organisator",
            "food": "vt",
            "food_display": "🧀 Vegetarisch",
            "money_total": 12.5,
            "money_items": [{
                "id": self.money.id,
                "amount": 12.5,
                "what": "Material",
                "date": self.money.date_added.isoformat().replace("+00:00", "Z"),
            }],
            "can_change_turnus": True,
        })
        self.assertEqual(payload["focuses"], [{
            "id": self.focus.id,
            "name": "Wald",
        }])
        self.assertEqual(payload["turnuses"], [
            {
                "id": self.other_turnus.id,
                "label": str(self.other_turnus),
            },
            {
                "id": self.turnus.id,
                "label": str(self.turnus),
            },
        ])
        self.assertNotContains(response, "Privates Kind")
        self.assertNotIn("team", payload)
        self.assertNotIn("kids", payload)

    def test_teamer_returns_only_selected_active_turnus_person(self):
        selected_user = User.objects.create_user(
            username="selected-teamer",
            email="grace@example.test",
        )
        selected = selected_user.profil
        selected.rufname = "Grace"
        selected.telefonnummer = "+4398765"
        selected.allergien = "Sellerie"
        selected.coffee = "Hafermilch"
        selected.rolle = "b"
        selected.essen = "vn"
        selected.turnus = self.turnus
        selected.save()
        selected_focus = Schwerpunkte.objects.create(
            swp_name="Theater",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w2"),
        )
        selected_focus.betreuende.add(selected)
        transaction = BetreuerinnenGeld.objects.create(
            who=selected,
            amount=-4.25,
            what="Rückgabe",
        )
        unrelated = User.objects.create_user(username="unrelated-teamer").profil
        unrelated.rufname = "Unrelated Private"
        unrelated.turnus = self.turnus
        unrelated.save()

        response = self.client.get(self.contract_url("teamer", selected))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"person", "focuses"})
        self.assertEqual(payload["person"], {
            "id": selected.id,
            "email": "grace@example.test",
            "rufname": "Grace",
            "phone": "+4398765",
            "allergies": "Sellerie",
            "coffee": "Hafermilch",
            "role": "b",
            "role_display": "Betreuer:in",
            "food": "vn",
            "food_display": "🥦 Vegan",
            "money_total": -4.25,
            "money_items": [{
                "id": transaction.id,
                "amount": -4.25,
                "what": "Rückgabe",
                "date": transaction.date_added.isoformat().replace(
                    "+00:00",
                    "Z",
                ),
            }],
        })
        self.assertEqual(payload["focuses"], [{
            "id": selected_focus.id,
            "name": "Theater",
        }])
        self.assertNotContains(response, "Unrelated Private")
        self.assertNotContains(response, "Privates Kind")
        self.assertNotIn("team", payload)
        self.assertNotIn("kids", payload)

    def test_teamer_rejects_cross_turnus_invalid_and_unscoped_requests(self):
        other = User.objects.create_user(username="other-turnus-teamer").profil
        other.rufname = "Other Turnus Private"
        other.turnus = self.other_turnus
        other.save()

        cross_turnus = self.client.get(self.contract_url("teamer", other))
        invalid = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "teamer"})
            + "?id=not-a-number",
        )
        unscoped_focus = Schwerpunkte.objects.create(
            swp_name="Unscoped Private Focus",
            schwerpunktzeit=None,
        )
        unscoped_focus.betreuende.add(self.profile)
        self.profile.turnus = None
        self.profile.save()
        unscoped = self.client.get(self.contract_url("teamer", other))
        own_profile = self.client.get(self.contract_url("profile"))

        self.assertEqual(cross_turnus.status_code, 404)
        self.assertEqual(invalid.status_code, 404)
        self.assertEqual(unscoped.status_code, 404)
        self.assertEqual(own_profile.status_code, 200)
        self.assertEqual(own_profile.json()["focuses"], [])
        self.assertNotContains(own_profile, "Unscoped Private Focus")
        self.assertNotContains(cross_turnus, "Other Turnus Private", status_code=404)

    def test_profile_contracts_require_authentication(self):
        self.client.logout()

        profile = self.client.get(self.contract_url("profile"))
        teamer = self.client.get(self.contract_url("teamer", self.profile))

        self.assertEqual(profile.status_code, 403)
        self.assertEqual(teamer.status_code, 403)

    def test_test_users_cannot_select_or_submit_a_different_turnus(self):
        self.user.groups.add(Group.objects.create(name="Test-users"))

        contract = self.client.get(self.contract_url("profile"))
        submitted = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/",
                "rufname": "Ada Test",
                "allergien": "Haselnüsse",
                "coffee": "Schwarz",
                "rolle": "o",
                "essen": "vt",
                "telefonnummer": "+4312345",
                "turnus": self.other_turnus.id,
            },
        )

        self.assertEqual(contract.status_code, 200)
        self.assertFalse(contract.json()["profile"]["can_change_turnus"])
        self.assertEqual(contract.json()["turnuses"], [])
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json(), {
            "ok": True,
            "redirect": "/dashboard/",
        })
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rufname, "Ada Test")
        self.assertEqual(self.profile.turnus, self.turnus)

        normal_user = User.objects.create_user(username="normal-after-test-user")
        normal_user.profil.turnus = self.turnus
        normal_user.profil.save()
        self.client.force_login(normal_user)
        normal_submission = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/",
                "rufname": "Normal user",
                "allergien": "",
                "coffee": "",
                "rolle": "b",
                "essen": "ft",
                "telefonnummer": "",
                "turnus": self.other_turnus.id,
            },
        )

        self.assertEqual(normal_submission.status_code, 200)
        normal_user.profil.refresh_from_db()
        self.assertEqual(normal_user.profil.turnus, self.other_turnus)

    def test_profile_form_preserves_validation_persistence_redirect_and_message(self):
        invalid = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/profil/",
                "rufname": "Not saved",
                "allergien": "Neu",
                "coffee": "Milch",
                "rolle": "b",
                "essen": "vn",
                "telefonnummer": "not-a-phone",
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
                "_target": "/profil/",
                "rufname": "Ada Neu",
                "allergien": "Keine",
                "coffee": "Milch",
                "rolle": "b",
                "essen": "vn",
                "telefonnummer": "+436641234567",
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
        self.assertEqual(self.profile.allergien, "Keine")
        self.assertEqual(self.profile.coffee, "Milch")
        self.assertEqual(self.profile.rolle, "b")
        self.assertEqual(self.profile.essen, "vn")
        self.assertEqual(str(self.profile.telefonnummer), "+436641234567")
        self.assertEqual(self.profile.turnus, self.other_turnus)
        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertEqual(bootstrap["profile"]["rufname"], "Ada Neu")
        self.assertEqual(bootstrap["turnus"]["id"], self.other_turnus.id)
        self.assertEqual(bootstrap["messages"], [{
            "text": "Profil upgedatet!",
            "tags": "success",
        }])

    def test_teamer_accounting_preserves_validation_redirect_and_active_turnus(self):
        selected = User.objects.create_user(username="accounting-teamer").profil
        selected.rufname = "Accounting"
        selected.turnus = self.turnus
        selected.save()
        other = User.objects.create_user(username="other-accounting").profil
        other.turnus = self.other_turnus
        other.save()

        invalid = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/teamer/{selected.id}/",
                "amount": "8.50",
                "what": "",
            },
        )
        cross_turnus = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/teamer/{other.id}/",
                "amount": "8.50",
                "what": "Nicht erlaubt",
            },
        )
        saved = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/teamer/{selected.id}/",
                "amount": "8.50",
                "what": "Einkauf",
            },
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertFalse(invalid.json()["ok"])
        self.assertEqual(cross_turnus.status_code, 404)
        self.assertFalse(other.betreuerinnen_geld.exists())
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json(), {
            "ok": True,
            "redirect": f"/teamer/{selected.id}/",
        })
        self.assertEqual(
            list(selected.betreuerinnen_geld.values("amount", "what")),
            [{"amount": 8.5, "what": "Einkauf"}],
        )


@override_settings(STORAGES=TEST_STORAGES)
class ProfileContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="profile-performance")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contract(self, key, profile=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        if profile:
            url = f"{url}?id={profile.id}"
        return measure_http_get(self.client, url)

    def test_profile_and_teamer_queries_stay_bounded_and_payloads_beat_legacy(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        selected = self.turnus.teamer.exclude(id=self.user.profil.id).first()
        small = {
            "profile": self.measure_contract("profile"),
            "teamer": self.measure_contract("teamer", selected),
        }

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        focuses = list(
            Schwerpunkte.objects.filter(schwerpunktzeit__turnus=self.turnus),
        )
        self.user.profil.swp.add(*focuses)
        selected.swp.add(*focuses)
        for index in range(30):
            BetreuerinnenGeld.objects.create(
                who=selected,
                amount=index + 0.5,
                what=f"Skalierender Einkauf {index}",
            )
        realistic = {
            "profile": self.measure_contract("profile"),
            "teamer": self.measure_contract("teamer", selected),
        }

        for key in small:
            with self.subTest(contract=key):
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 9)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 1)
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
