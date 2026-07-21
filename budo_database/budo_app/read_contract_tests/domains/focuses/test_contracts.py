from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import Auslagerorte, Kinder, Schwerpunkte, Turnus
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


class FocusContractTests(TestCase):
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
            username="focus-user",
            password="secret",
        )
        self.user.profil.rufname = "Ada Teamer"
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.carer = User.objects.create_user(username="focus-carer").profil
        self.carer.rufname = "Grace"
        self.carer.turnus = self.turnus
        self.carer.save()
        self.other_carer = User.objects.create_user(
            username="other-focus-carer",
        ).profil
        self.other_carer.rufname = "Other"
        self.other_carer.turnus = self.other_turnus
        self.other_carer.save()
        self.place = Auslagerorte.objects.create(
            name="Waldplatz",
            koordinaten="48.5, 15.0",
        )
        self.focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            beschreibung="Bäume kennenlernen",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w1"),
            ort=self.place,
            auslagern=True,
        )
        self.focus.betreuende.add(self.carer)
        self.focus.meals.filter(day=1, meal_type="lunch").update(
            meal_choice="warm",
        )
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Kind",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=False,
            budo_family="M",
            sex="weiblich",
            illness="Private Krankheit",
            notfall_kontakte="Privater Notfallkontakt",
        )
        self.kid.schwerpunkte.add(self.focus)
        self.other_focus = Schwerpunkte.objects.create(
            swp_name="Fremder Schwerpunkt",
            schwerpunktzeit=self.other_turnus.schwerpunktzeit_set.get(
                woche="w1",
            ),
        )
        self.other_focus.betreuende.add(self.other_carer)
        self.other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Kind",
            kid_birthday=date(2012, 8, 2),
            turnus=self.other_turnus,
        )
        # Even malformed cross-Turnus relations must not leak into a focused read.
        self.other_kid.schwerpunkte.add(self.focus, self.other_focus)
        self.client.force_login(self.user)

    def contract_url(self, key, focus=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={focus.id}" if focus else url

    def test_dashboard_returns_only_active_turnus_summary_fields(self):
        response = self.client.get(self.contract_url("focus-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "focuses": [{
                "id": self.focus.id,
                "name": "Wald",
                "week": "w1",
                "place_id": self.place.id,
                "place": "Waldplatz",
                "coordinates": "48.5, 15.0",
                "carers": "Grace",
                "off_site": True,
                "kid_count": 1,
                "meals_assigned": True,
            }],
        })
        self.assertNotContains(response, "Fremder Schwerpunkt")
        self.assertNotContains(response, "Private Krankheit")
        self.assertNotContains(response, "Privater Notfallkontakt")

    def test_dashboard_ignores_a_cross_turnus_carer_linked_to_a_focus(self):
        self.focus.betreuende.add(self.other_carer)

        response = self.client.get(self.contract_url("focus-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["focuses"][0]["carers"], "Grace")
        self.assertNotContains(response, "Other")

    def test_detail_returns_one_focus_assignments_timing_place_and_meals(self):
        response = self.client.get(self.contract_url("focus-detail", self.focus))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"focus", "kids"})
        focus = response.json()["focus"]
        self.assertEqual(focus, {
            "id": self.focus.id,
            "name": "Wald",
            "description": "Bäume kennenlernen",
            "week": "w1",
            "time": str(self.focus.schwerpunktzeit),
            "time_id": self.focus.schwerpunktzeit_id,
            "duration": 3,
            "start": "2026-07-05",
            "off_site": True,
            "place_id": self.place.id,
            "place": "Waldplatz",
            "coordinates": "48.5, 15.0",
            "carers": "Grace",
            "carer_ids": [self.carer.id],
            "meals": {
                "1": {"breakfast": "", "lunch": "warm", "dinner": ""},
                "2": {"breakfast": "", "lunch": "", "dinner": ""},
                "3": {"breakfast": "", "lunch": "", "dinner": ""},
            },
        })
        self.assertEqual(response.json()["kids"], [{
            "id": self.kid.id,
            "full_name": "Ada Kind",
            "present": False,
            "budo_family": "M",
            "sex_short": "♀",
            "age": 14.0,
            "birthday_during_turnus": True,
            "food": "🥩",
            "drugs": "",
            "illness": "Private Krankheit",
        }])
        self.assertNotContains(response, "Privater Notfallkontakt")
        self.assertNotContains(response, "Other Kind")

    def test_detail_ignores_a_cross_turnus_carer_linked_to_the_focus(self):
        self.focus.betreuende.add(self.other_carer)

        response = self.client.get(
            self.contract_url("focus-detail", self.focus),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["focus"]["carers"], "Grace")
        self.assertEqual(response.json()["focus"]["carer_ids"], [self.carer.id])
        self.assertNotContains(response, "Other")

    def test_create_and_update_contracts_return_scoped_options_and_values(self):
        create = self.client.get(self.contract_url("focus-create"))
        update = self.client.get(self.contract_url("focus-update", self.focus))

        expected_options = {
            "places": [{"id": self.place.id, "name": "Waldplatz"}],
            "team": [
                {"id": self.user.profil.id, "rufname": "Ada Teamer"},
                {"id": self.carer.id, "rufname": "Grace"},
            ],
            "focus_times": [
                {
                    "id": item.id,
                    "label": str(item),
                    "week": item.woche,
                    "duration": item.dauer,
                    "start": item.swp_beginn.isoformat(),
                }
                for item in self.turnus.schwerpunktzeit_set.order_by(
                    "woche",
                    "id",
                )
            ],
        }
        self.assertEqual(create.status_code, 200)
        self.assertEqual(create.json(), expected_options)
        self.assertEqual(update.status_code, 200)
        self.assertEqual(
            set(update.json()),
            {"focus", "places", "team", "focus_times"},
        )
        self.assertEqual(
            {key: update.json()[key] for key in expected_options},
            expected_options,
        )
        self.assertEqual(update.json()["focus"], {
            "id": self.focus.id,
            "name": "Wald",
            "description": "Bäume kennenlernen",
            "time_id": self.focus.schwerpunktzeit_id,
            "off_site": True,
            "place_id": self.place.id,
            "carer_ids": [self.carer.id],
        })
        self.assertNotContains(update, "Other")

    def test_update_ignores_a_cross_turnus_carer_linked_to_the_focus(self):
        self.focus.betreuende.add(self.other_carer)

        response = self.client.get(
            self.contract_url("focus-update", self.focus),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["focus"]["carer_ids"], [self.carer.id])
        self.assertNotContains(response, "Other")

    def test_meals_contract_returns_only_the_focus_and_editable_choices(self):
        response = self.client.get(self.contract_url("focus-meals", self.focus))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {
            "focus",
            "meal_choices",
            "meal_types",
        })
        self.assertEqual(response.json()["focus"]["id"], self.focus.id)
        self.assertEqual(response.json()["focus"]["name"], "Wald")
        self.assertEqual(len(response.json()["focus"]["meal_items"]), 9)
        lunch = next(
            item
            for item in response.json()["focus"]["meal_items"]
            if item["day"] == 1 and item["type"] == "lunch"
        )
        self.assertEqual(lunch, {
            "id": self.focus.meals.get(day=1, meal_type="lunch").id,
            "day": 1,
            "type": "lunch",
            "choice": "warm",
        })
        self.assertEqual(response.json()["meal_choices"], [
            {"value": "", "label": "---------"},
            {"value": "box", "label": "Box"},
            {"value": "budo", "label": "Im BuDo"},
            {"value": "warm", "label": "Warm geliefert"},
        ])
        self.assertEqual(response.json()["meal_types"], {
            "breakfast": "Frühstück",
            "lunch": "Mittagessen",
            "dinner": "Abendessen",
        })

    def test_entity_contracts_reject_cross_turnus_and_invalid_identifiers(self):
        for key in ("focus-detail", "focus-update", "focus-meals"):
            with self.subTest(contract=key):
                cross_turnus = self.client.get(
                    self.contract_url(key, self.other_focus),
                )
                invalid = self.client.get(
                    reverse("route-data-api", kwargs={"contract_key": key})
                    + "?id=not-a-number",
                )
                self.assertEqual(cross_turnus.status_code, 404)
                self.assertEqual(invalid.status_code, 404)

    def test_all_focus_contracts_require_authentication(self):
        self.client.logout()

        for key in (
            "focus-create",
            "focus-dashboard",
            "focus-detail",
            "focus-meals",
            "focus-update",
        ):
            with self.subTest(contract=key):
                response = self.client.get(
                    self.contract_url(
                        key,
                        self.focus if key not in ("focus-create", "focus-dashboard") else None,
                    ),
                )
                self.assertEqual(response.status_code, 403)

    def test_user_without_active_turnus_gets_no_unscoped_focus_data_or_options(self):
        user_without_turnus = User.objects.create_user(username="no-focus-turnus")
        self.client.force_login(user_without_turnus)

        dashboard = self.client.get(self.contract_url("focus-dashboard"))
        create = self.client.get(self.contract_url("focus-create"))
        detail = self.client.get(self.contract_url("focus-detail", self.focus))
        submitted = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/schwerpunkt/create",
                "swp_name": "Unscoped",
                "betreuende": [self.carer.id],
                "schwerpunktzeit": self.focus.schwerpunktzeit_id,
            },
        )

        self.assertEqual(dashboard.json(), {"focuses": []})
        self.assertEqual(create.json(), {
            "places": [],
            "team": [],
            "focus_times": [],
        })
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(submitted.status_code, 422)
        self.assertFalse(Schwerpunkte.objects.filter(swp_name="Unscoped").exists())

    def test_update_keeps_validation_redirect_message_and_search_label_current(self):
        invalid = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/schwerpunkt/{self.focus.id}/update",
                "swp_name": "",
                "schwerpunktzeit": self.focus.schwerpunktzeit_id,
            },
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertFalse(invalid.json()["ok"])
        self.assertTrue(invalid.json()["errors"])

        self.focus.auslagern = False
        self.focus.save(update_fields=["auslagern"])
        saved = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/schwerpunkt/{self.focus.id}/update",
                "swp_name": "Neuer Waldname",
                "ort": self.place.id,
                "betreuende": [self.carer.id],
                "beschreibung": "Aktualisiert",
                "schwerpunktzeit": self.focus.schwerpunktzeit_id,
                "auslagern": "on",
            },
        )

        self.assertEqual(saved.status_code, 200)
        self.focus.refresh_from_db()
        self.assertTrue(self.focus.auslagern)
        self.assertEqual(saved.json(), {
            "ok": True,
            "redirect": f"/schwerpunkt/{self.focus.id}/",
        })
        update_payload = self.client.get(
            self.contract_url("focus-update", self.focus),
        ).json()
        self.assertEqual(update_payload["focus"]["name"], "Neuer Waldname")
        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertIn(
            {"id": self.focus.id, "name": "Neuer Waldname"},
            bootstrap["search_index"]["focuses"],
        )
        self.assertEqual(bootstrap["messages"], [{
            "text": "Schwerpunkt upgedatet!",
            "tags": "success",
        }])

    def test_cross_turnus_update_and_related_options_cannot_be_submitted(self):
        cross_entity = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/schwerpunkt/{self.other_focus.id}/update",
                "swp_name": "Gestohlen",
                "schwerpunktzeit": self.other_focus.schwerpunktzeit_id,
            },
        )
        cross_options = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/schwerpunkt/{self.focus.id}/update",
                "swp_name": "Nicht speichern",
                "betreuende": [self.other_carer.id],
                "schwerpunktzeit": self.other_focus.schwerpunktzeit_id,
            },
        )

        self.assertEqual(cross_entity.status_code, 404)
        self.assertEqual(cross_options.status_code, 422)
        self.focus.refresh_from_db()
        self.other_focus.refresh_from_db()
        self.assertEqual(self.focus.swp_name, "Wald")
        self.assertEqual(self.other_focus.swp_name, "Fremder Schwerpunkt")

    def test_create_uses_active_options_and_preserves_redirect_and_message(self):
        rejected = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/schwerpunkt/create",
                "swp_name": "Falscher Turnus",
                "betreuende": [self.other_carer.id],
                "schwerpunktzeit": self.other_focus.schwerpunktzeit_id,
            },
        )

        self.assertEqual(rejected.status_code, 422)
        self.assertFalse(
            Schwerpunkte.objects.filter(swp_name="Falscher Turnus").exists(),
        )

        created = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/schwerpunkt/create",
                "swp_name": "Theater",
                "ort": self.place.id,
                "betreuende": [self.carer.id],
                "beschreibung": "Bühne",
                "schwerpunktzeit": self.focus.schwerpunktzeit_id,
                "auslagern": "",
            },
        )

        focus = Schwerpunkte.objects.get(swp_name="Theater")
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json(), {
            "ok": True,
            "redirect": f"/schwerpunkt/{focus.id}/",
        })
        self.assertEqual(list(focus.betreuende.all()), [self.carer])
        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertIn(
            {"id": focus.id, "name": "Theater"},
            bootstrap["search_index"]["focuses"],
        )
        self.assertEqual(bootstrap["messages"], [{
            "text": "Schwerpunkt hinzugefügt!",
            "tags": "success",
        }])

    def test_meal_form_saves_and_cross_turnus_meals_cannot_be_altered(self):
        meals = list(self.focus.meals.order_by("day", "id"))
        payload = {
            "_target": f"/swpmeals/{self.focus.id}",
            "form-TOTAL_FORMS": len(meals),
            "form-INITIAL_FORMS": len(meals),
        }
        for index, meal in enumerate(meals):
            payload[f"form-{index}-id"] = meal.id
            payload[f"form-{index}-meal_choice"] = (
                "box" if meal.day == 1 and meal.meal_type == "breakfast" else meal.meal_choice
            )

        saved = self.client.post(reverse("form-submit-api"), payload)

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json(), {
            "ok": True,
            "redirect": f"/schwerpunkt/{self.focus.id}/",
        })
        refreshed = self.client.get(
            self.contract_url("focus-meals", self.focus),
        ).json()
        breakfast = next(
            item
            for item in refreshed["focus"]["meal_items"]
            if item["day"] == 1 and item["type"] == "breakfast"
        )
        self.assertEqual(breakfast["choice"], "box")

        other_meals = list(self.other_focus.meals.order_by("day", "id"))
        cross_payload = {
            "_target": f"/swpmeals/{self.other_focus.id}",
            "form-TOTAL_FORMS": len(other_meals),
            "form-INITIAL_FORMS": len(other_meals),
        }
        for index, meal in enumerate(other_meals):
            cross_payload[f"form-{index}-id"] = meal.id
            cross_payload[f"form-{index}-meal_choice"] = "warm"

        rejected = self.client.post(reverse("form-submit-api"), cross_payload)

        self.assertEqual(rejected.status_code, 404)
        self.assertFalse(
            self.other_focus.meals.filter(meal_choice="warm").exists(),
        )


@override_settings(STORAGES=TEST_STORAGES)
class FocusContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="focus-performance")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def contract_url(self, key, focus=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={focus.id}" if focus else url

    def test_dashboard_query_growth_is_bounded_and_payload_beats_legacy(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = measure_http_get(
            self.client,
            self.contract_url("focus-dashboard"),
        )

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(
            self.client,
            self.contract_url("focus-dashboard"),
        )

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(realistic.response.json()["focuses"]), 8)
        self.assertQueryCountAtMost(realistic, 8)
        self.assertQueryGrowthAtMost(small, realistic, 1)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )

    def test_detail_query_growth_is_bounded_as_assignments_increase(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        focus = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=self.turnus,
        ).order_by("id").first()
        small = measure_http_get(
            self.client,
            self.contract_url("focus-detail", focus),
        )

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(
            self.client,
            self.contract_url("focus-detail", focus),
        )

        self.assertEqual(realistic.status_code, 200)
        self.assertGreater(
            len(realistic.response.json()["kids"]),
            len(small.response.json()["kids"]),
        )
        self.assertQueryCountAtMost(realistic, 10)
        self.assertQueryGrowthAtMost(small, realistic, 1)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
