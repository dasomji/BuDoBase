from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import (
    Auslagerorte,
    Kinder,
    Profil,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)
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


class KitchenContractTests(TestCase):
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
            username="kitchen-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.rufname = "Kathi"
        self.user.profil.essen = "vt"
        self.user.profil.allergien = "Haselnüsse"
        self.user.profil.save()

        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=False,
            vegetarisch="ja",
            special_food_description="glutenfrei",
            sozialversicherungsnr="1234 020712",
            notfall_kontakte="Private Kontaktperson",
            anmelder_vorname="Grace",
            anmelder_email="private@example.test",
            anmerkung="Private Notiz",
            pfand=5,
        )
        place = Auslagerorte.objects.create(name="Waldhaus")
        week = self.turnus.schwerpunktzeit_set.get(woche="w1")
        week.dauer = 1
        week.save()
        self.focus = Schwerpunkte.objects.create(
            swp_name="Waldküche",
            schwerpunktzeit=week,
            ort=place,
        )
        self.focus.swp_kinder.add(self.kid)
        self.focus.meals.filter(
            day=1,
            meal_type="lunch",
        ).update(meal_choice="warm")
        self.client.force_login(self.user)

    def contract_url(self):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "kitchen"},
        )

    def test_returns_the_active_turnus_kitchen_projection(self):
        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "kids": [
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Lovelace",
                        "present": False,
                        "food": "🌱 - glutenfrei",
                        "special_food": "glutenfrei",
                    }
                ],
                "team": [
                    {
                        "id": self.user.profil.id,
                        "rufname": "Kathi",
                        "food_display": "🧀 Vegetarisch",
                        "allergies": "Haselnüsse",
                    }
                ],
                "focuses": [
                    {
                        "id": self.focus.id,
                        "name": "Waldküche",
                        "week": "w1",
                        "duration": 1,
                        "kid_count": 1,
                        "carer_count": 0,
                        "carers": "",
                        "dietary_counts": {
                            "flexitarian": 0,
                            "vegetarian": 1,
                            "vegan": 0,
                        },
                        "intolerances": {
                            "kids": [
                                {
                                    "name": "Ada Lovelace",
                                    "diet": "vegetarian",
                                    "details": "glutenfrei",
                                }
                            ],
                            "team": [],
                        },
                        "meals": [
                            {
                                "day": 1,
                                "type": "breakfast",
                                "choice": "",
                            },
                            {
                                "day": 1,
                                "type": "lunch",
                                "choice": "warm",
                            },
                            {
                                "day": 1,
                                "type": "dinner",
                                "choice": "",
                            },
                        ],
                    }
                ],
            },
        )

    def test_excludes_cross_turnus_records_and_unrelated_private_fields(self):
        other_user = User.objects.create_user(username="other-kitchen-user")
        other_user.profil.turnus = self.other_turnus
        other_user.profil.rufname = "Other Teamer"
        other_user.profil.allergien = "Private other allergy"
        other_user.profil.save()
        other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Kind",
            turnus=self.other_turnus,
            special_food_description="Private other food",
            sozialversicherungsnr="private",
            notfall_kontakte="private",
            anmelder_email="private@example.test",
            anmerkung="private",
            pfand=10,
        )
        other_focus = Schwerpunkte.objects.create(
            swp_name="Other Focus",
            schwerpunktzeit=self.other_turnus.schwerpunktzeit_set.get(
                woche="w1",
            ),
        )
        other_focus.swp_kinder.add(other_kid)
        self.focus.swp_kinder.add(other_kid)
        self.focus.betreuende.add(other_user.profil)
        unplanned_time = Schwerpunktzeit.objects.create(
            woche="u",
            turnus=self.turnus,
            swp_beginn=date(2026, 7, 1),
            dauer=1,
        )
        Schwerpunkte.objects.create(
            swp_name="Unplanned Focus",
            schwerpunktzeit=unplanned_time,
        )

        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Other")
        self.assertNotContains(response, "Unplanned Focus")
        payload = response.json()
        self.assertEqual(payload["focuses"][0]["kid_count"], 1)
        self.assertEqual(payload["focuses"][0]["carers"], "")
        self.assertEqual(
            set(payload["kids"][0]),
            {"id", "full_name", "present", "food", "special_food"},
        )
        self.assertEqual(
            set(payload["team"][0]),
            {"id", "rufname", "food_display", "allergies"},
        )
        self.assertEqual(
            set(payload["focuses"][0]),
            {
                "id",
                "name",
                "week",
                "duration",
                "kid_count",
                "carer_count",
                "carers",
                "dietary_counts",
                "intolerances",
                "meals",
            },
        )
        response_text = response.content.decode()
        for private_value in (
            "1234 020712",
            "Private Kontaktperson",
            "private@example.test",
            "Private Notiz",
        ):
            self.assertNotIn(private_value, response_text)
        for private_field in (
            "social_security_number",
            "emergency_contacts",
            "registrant_email",
            "note",
            "notes",
            "transactions",
            "deposit",
            "pocket_money",
            "phone",
            "email",
        ):
            self.assertNotIn(private_field, response_text)

    def test_summarizes_diets_and_intolerances_for_kids_and_carers(self):
        flexitarian_kid = Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Berta",
            kid_nachname="Box",
            turnus=self.turnus,
            vegetarisch="nein",
            special_food_description="Laktose",
        )
        vegan_user = User.objects.create_user(username="vegan-kitchen")
        vegan_profile = Profil.objects.get(user=vegan_user)
        vegan_profile.turnus = self.turnus
        vegan_profile.rufname = "Vera"
        vegan_profile.essen = "vn"
        vegan_profile.allergien = "Soja"
        vegan_profile.save()
        self.focus.swp_kinder.add(flexitarian_kid)
        self.focus.betreuende.add(self.user.profil, vegan_profile)

        focus = self.client.get(self.contract_url()).json()["focuses"][0]

        self.assertEqual(focus["carer_count"], 2)
        self.assertEqual(
            focus["dietary_counts"],
            {"flexitarian": 1, "vegetarian": 2, "vegan": 1},
        )
        self.assertEqual(
            focus["intolerances"],
            {
                "kids": [
                    {
                        "name": "Ada Lovelace",
                        "diet": "vegetarian",
                        "details": "glutenfrei",
                    },
                    {
                        "name": "Berta Box",
                        "diet": "flexitarian",
                        "details": "Laktose",
                    },
                ],
                "team": [
                    {
                        "name": "Kathi",
                        "diet": "vegetarian",
                        "details": "Haselnüsse",
                    },
                    {
                        "name": "Vera",
                        "diet": "vegan",
                        "details": "Soja",
                    },
                ],
            },
        )

    def test_requires_authentication_and_has_safe_no_turnus_behavior(self):
        self.client.logout()

        unauthenticated = self.client.get(self.contract_url())

        self.assertEqual(unauthenticated.status_code, 403)

        user_without_turnus = User.objects.create_user(username="no-turnus")
        self.client.force_login(user_without_turnus)

        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"kids": [], "team": [], "focuses": []})

    def test_orders_every_kitchen_collection_deterministically(self):
        Kinder.objects.create(
            kid_index="T2-0",
            kid_vorname="Aaron",
            kid_nachname="First",
            turnus=self.turnus,
        )
        second_user = User.objects.create_user(username="aaron-kitchen")
        second_user.profil.turnus = self.turnus
        second_user.profil.rufname = "Aaron"
        second_user.profil.save()
        week_2 = self.turnus.schwerpunktzeit_set.get(woche="w2")
        Schwerpunkte.objects.create(
            swp_name="Alpha",
            schwerpunktzeit=week_2,
        )

        payload = self.client.get(self.contract_url()).json()

        self.assertEqual(
            [kid["full_name"] for kid in payload["kids"]],
            ["Aaron First", "Ada Lovelace"],
        )
        self.assertEqual(
            [member["rufname"] for member in payload["team"]],
            ["Aaron", "Kathi"],
        )
        self.assertEqual(
            [(focus["week"], focus["name"]) for focus in payload["focuses"]],
            [("w1", "Waldküche"), ("w2", "Alpha")],
        )


@override_settings(STORAGES=TEST_STORAGES)
class KitchenContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kitchen-performance",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contract(self):
        return measure_http_get(
            self.client,
            reverse(
                "route-data-api",
                kwargs={"contract_key": "kitchen"},
            ),
        )

    def test_query_growth_is_bounded_and_payload_beats_the_legacy_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = self.measure_contract()

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = self.measure_contract()

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertQueryCountAtMost(realistic, 12)
        self.assertQueryGrowthAtMost(small, realistic, 1)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
