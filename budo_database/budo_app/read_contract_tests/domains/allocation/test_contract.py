import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import (
    Kinder,
    Schwerpunkte,
    SchwerpunktWahl,
    Schwerpunktzeit,
    Turnus,
)
from budo_app.read_contract_tests.fixtures import ActiveTurnusFixtureFactory
from budo_app.read_contracts.measurement import QueryBudgetAssertions, measure_http_get


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


class AllocationContractTests(TestCase):
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
            username="allocation-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)

        self.week_1 = Schwerpunktzeit.objects.get(turnus=self.turnus, woche="w1")
        self.week_2 = Schwerpunktzeit.objects.get(turnus=self.turnus, woche="w2")
        self.other_week_2 = Schwerpunktzeit.objects.get(
            turnus=self.other_turnus,
            woche="w2",
        )
        self.forest = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=self.week_1,
        )
        self.lake = Schwerpunkte.objects.create(
            swp_name="See",
            schwerpunktzeit=self.week_2,
        )
        self.other_focus = Schwerpunkte.objects.create(
            swp_name="Fremder Turnus",
            schwerpunktzeit=self.other_week_2,
        )
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Kind",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            geschwister="Bea",
            illness="Private Krankheit",
            drugs="Private Medikamente",
            notfall_kontakte="Privater Notfallkontakt",
            anmelder_vorname="Eltern",
            anmelder_nachname="Kind",
            anmelder_email="private@example.test",
            rechnungsadresse="Privatweg 1",
            rechnung_ort="Wien",
            rechnung_land="AT",
        )
        self.other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Kind",
            kid_birthday=date(2012, 8, 2),
            turnus=self.other_turnus,
        )
        self.kid.schwerpunkte.add(self.forest, self.lake, self.other_focus)
        self.other_kid.schwerpunkte.add(self.other_focus)
        SchwerpunktWahl.objects.create(
            kind=self.kid,
            schwerpunktzeit=self.week_1,
            erste_wahl=self.forest,
            freunde="Woche-eins-Freund",
        )
        SchwerpunktWahl.objects.create(
            kind=self.kid,
            schwerpunktzeit=self.week_2,
            erste_wahl=self.lake,
            zweite_wahl=self.other_focus,
            freunde="Woche-zwei-Freund",
        )
        SchwerpunktWahl.objects.create(
            kind=self.other_kid,
            schwerpunktzeit=self.other_week_2,
            erste_wahl=self.other_focus,
            freunde="Fremder Freund",
        )

    def contract_url(self, week):
        return f'{reverse("route-data-api", kwargs={"contract_key": "allocation"})}?week={week}'

    def test_selected_week_contract_is_active_turnus_only_and_privacy_focused(self):
        response = self.client.get(self.contract_url(2))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "kids": [
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Kind",
                        "age": self.kid.get_alter(),
                        "siblings": "Bea",
                        "focus_ids": [self.lake.id],
                        "choices": [
                            {
                                "week": "w2",
                                "first": self.lake.id,
                                "second": None,
                                "third": None,
                                "friends": "Woche-zwei-Freund",
                            }
                        ],
                    }
                ],
                "focuses": [
                    {
                        "id": self.lake.id,
                        "name": "See",
                        "week": "w2",
                        "kid_ids": [self.kid.id],
                    }
                ],
            },
        )

    def test_week_one_selects_only_week_one_assignments_choices_and_friends(self):
        payload = self.client.get(self.contract_url(1)).json()

        self.assertEqual(
            payload["focuses"],
            [
                {
                    "id": self.forest.id,
                    "name": "Wald",
                    "week": "w1",
                    "kid_ids": [self.kid.id],
                }
            ],
        )
        self.assertEqual(payload["kids"][0]["focus_ids"], [self.forest.id])
        self.assertEqual(
            payload["kids"][0]["choices"],
            [
                {
                    "week": "w1",
                    "first": self.forest.id,
                    "second": None,
                    "third": None,
                    "friends": "Woche-eins-Freund",
                }
            ],
        )

    def test_contract_requires_authentication_and_a_supported_week(self):
        self.client.logout()

        unauthenticated = self.client.get(self.contract_url(1))

        self.assertEqual(unauthenticated.status_code, 403)

        self.client.force_login(self.user)
        for week in ("", "0", "3", "w2"):
            with self.subTest(week=week):
                response = self.client.get(self.contract_url(week))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(),
                    {"detail": "Allocation week must be 1 or 2."},
                )

    def test_contract_without_an_active_turnus_does_not_return_unscoped_records(self):
        user_without_turnus = User.objects.create_user(username="no-active-turnus")
        orphaned_kid = Kinder.objects.create(
            kid_index="NO-TURNUS",
            kid_vorname="Orphaned",
            kid_nachname="Record",
            kid_birthday=date(2012, 7, 2),
            turnus=None,
        )
        self.client.force_login(user_without_turnus)

        response = self.client.get(self.contract_url(2))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"kids": [], "focuses": []})
        self.assertNotContains(response, orphaned_kid.kid_vorname)

    def test_existing_json_mutations_are_visible_in_the_selected_week_contract(self):
        climbing = Schwerpunkte.objects.create(
            swp_name="Klettern",
            schwerpunktzeit=self.week_2,
        )

        choice_response = self.client.post(
            reverse("update_schwerpunkt_wahl"),
            json.dumps(
                {
                    "kid_id": self.kid.id,
                    "swp_id": climbing.id,
                    "choice_rank": "1",
                }
            ),
            content_type="application/json",
        )
        friends_response = self.client.post(
            reverse("update_freunde"),
            json.dumps(
                {
                    "kid_id": self.kid.id,
                    "freunde": "Neue Woche-zwei-Freunde",
                    "week": "2",
                }
            ),
            content_type="application/json",
        )
        payload = self.client.get(self.contract_url(2)).json()

        self.assertEqual(choice_response.status_code, 200)
        self.assertEqual(choice_response.json(), {"status": "success"})
        self.assertEqual(friends_response.status_code, 200)
        self.assertEqual(friends_response.json(), {"status": "success"})
        kid = payload["kids"][0]
        focuses = {focus["name"]: focus for focus in payload["focuses"]}
        self.assertEqual(kid["focus_ids"], [climbing.id])
        self.assertEqual(
            kid["choices"],
            [
                {
                    "week": "w2",
                    "first": climbing.id,
                    "second": None,
                    "third": None,
                    "friends": "Neue Woche-zwei-Freunde",
                }
            ],
        )
        self.assertEqual(focuses["Klettern"]["kid_ids"], [self.kid.id])
        self.assertEqual(focuses["See"]["kid_ids"], [])

    def test_existing_json_mutations_cannot_change_cross_turnus_records(self):
        original_focus_ids = set(self.kid.schwerpunkte.values_list("id", flat=True))
        original_other_friends = SchwerpunktWahl.objects.get(
            kind=self.other_kid,
            schwerpunktzeit=self.other_week_2,
        ).freunde

        foreign_focus_response = self.client.post(
            reverse("update_schwerpunkt_wahl"),
            json.dumps(
                {
                    "kid_id": self.kid.id,
                    "swp_id": self.other_focus.id,
                    "choice_rank": None,
                }
            ),
            content_type="application/json",
        )
        foreign_kid_response = self.client.post(
            reverse("update_freunde"),
            json.dumps(
                {
                    "kid_id": self.other_kid.id,
                    "freunde": "Manipuliert",
                    "week": "2",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(foreign_focus_response.json()["status"], "error")
        self.assertEqual(foreign_kid_response.status_code, 404)
        self.assertEqual(
            set(self.kid.schwerpunkte.values_list("id", flat=True)),
            original_focus_ids,
        )
        self.assertEqual(
            SchwerpunktWahl.objects.get(
                kind=self.other_kid,
                schwerpunktzeit=self.other_week_2,
            ).freunde,
            original_other_friends,
        )


@override_settings(STORAGES=TEST_STORAGES)
class AllocationContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="allocation-performance-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)
        self.contract_url = (
            f'{reverse("route-data-api", kwargs={"contract_key": "allocation"})}'
            "?week=2"
        )

    def test_query_growth_is_bounded_and_payload_is_smaller_than_legacy(self):
        self.fixtures.grow_to(kids=3, focuses=4, team=2, places=1)
        small = measure_http_get(self.client, self.contract_url)

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(self.client, self.contract_url)
        legacy = measure_http_get(self.client, reverse("app-data-api"))

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(realistic.response.json()["kids"]), 48)
        self.assertQueryCountAtMost(realistic, 10)
        self.assertQueryGrowthAtMost(small, realistic, 2)
        self.assertLess(realistic.response_bytes, legacy.response_bytes)
        self.assertGreaterEqual(realistic.sql_time_ms, 0)
