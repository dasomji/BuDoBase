import json
from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from budo_app.models import Geld, Kinder, Turnus
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


class AttendanceContractTests(TestCase):
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
            username="attendance-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.active_kid = self.create_kid(
            turnus=self.turnus,
            index="T2-1",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.other_kid = self.create_kid(
            turnus=self.other_turnus,
            index="T3-1",
            first_name="Other",
            last_name="Turnus",
        )
        self.client.force_login(self.user)

    def create_kid(self, *, turnus, index, first_name, last_name, **fields):
        defaults = {
            "kid_index": index,
            "kid_vorname": first_name,
            "kid_nachname": last_name,
            "kid_birthday": date(2012, 7, 2),
            "turnus": turnus,
            "anmelder_vorname": "Grace",
            "anmelder_nachname": "Hopper",
            "anmelder_mobil": "+4312345",
            "rechnungsadresse": "Teststraße 1",
            "rechnung_ort": "Wien",
            "rechnung_land": "AT",
        }
        defaults.update(fields)
        return Kinder.objects.create(**defaults)

    def contract_url(self, key, kid=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={kid.id}" if kid else url

    def test_check_in_returns_only_the_selected_active_turnus_kid(self):
        self.active_kid.anwesend = False
        self.active_kid.ausweis = True
        self.active_kid.e_card = False
        self.active_kid.einverstaendnis_erklaerung = True
        self.active_kid.illness = "must stay private"
        self.active_kid.notfall_kontakte = "must stay private"
        self.active_kid.save()
        self.create_kid(
            turnus=self.turnus,
            index="T2-2",
            first_name="Second",
            last_name="Active",
        )

        response = self.client.get(self.contract_url("check-in", self.active_kid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "kid": {
                "id": self.active_kid.id,
                "full_name": "Ada Lovelace",
                "present": False,
                "id_card": True,
                "e_card": False,
                "consent": True,
            },
        })

    def test_all_attendance_contracts_require_authentication(self):
        self.client.logout()

        responses = {
            "check-in": self.client.get(
                self.contract_url("check-in", self.active_kid),
            ),
            "check-out": self.client.get(
                self.contract_url("check-out", self.active_kid),
            ),
            "train-arrival": self.client.get(
                self.contract_url("train-arrival"),
            ),
            "train-departure": self.client.get(
                self.contract_url("train-departure"),
            ),
        }

        for key, response in responses.items():
            with self.subTest(contract=key):
                self.assertEqual(response.status_code, 403)

    def test_check_in_does_not_expose_a_cross_turnus_kid(self):
        response = self.client.get(self.contract_url("check-in", self.other_kid))

        self.assertEqual(response.status_code, 404)

    def test_check_out_returns_the_selected_kid_and_current_pocket_money(self):
        self.active_kid.anwesend = True
        self.active_kid.ausweis = True
        self.active_kid.e_card = True
        self.active_kid.einverstaendnis_erklaerung = False
        self.active_kid.illness = "must stay private"
        self.active_kid.save()
        Geld.objects.create(
            kinder=self.active_kid,
            added_by=self.user,
            amount=20,
        )
        Geld.objects.create(
            kinder=self.active_kid,
            added_by=self.user,
            amount=-7.5,
        )

        response = self.client.get(self.contract_url("check-out", self.active_kid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "kid": {
                "id": self.active_kid.id,
                "full_name": "Ada Lovelace",
                "present": True,
                "id_card": True,
                "e_card": True,
                "consent": False,
                "pocket_money": 12.5,
            },
        })

    def test_check_out_does_not_expose_a_cross_turnus_kid(self):
        response = self.client.get(self.contract_url("check-out", self.other_kid))

        self.assertEqual(response.status_code, 404)

    def test_train_arrival_returns_only_arriving_active_turnus_kids(self):
        self.active_kid.anwesend = True
        self.active_kid.zug_anreise = True
        self.active_kid.top_jugendticket = True
        self.active_kid.geschwister = "Charles"
        self.active_kid.illness = "must stay private"
        self.active_kid.save()
        self.create_kid(
            turnus=self.turnus,
            index="T2-2",
            first_name="Not",
            last_name="Arriving",
            zug_anreise=False,
        )
        self.other_kid.zug_anreise = True
        self.other_kid.save()

        response = self.client.get(self.contract_url("train-arrival"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "kids": [{
                "id": self.active_kid.id,
                "full_name": "Ada Lovelace",
                "present": True,
                "train_arrival": True,
                "youth_ticket": True,
                "age": 14.0,
                "registrant_name": "Grace Hopper",
                "registrant_phone": "+4312345",
                "siblings": "Charles",
            }],
            "totals": {
                "train_arrival": 1,
                "with_youth_ticket": 1,
                "without_youth_ticket": 0,
            },
        })

    def test_train_departure_returns_all_active_turnus_kids_and_notes(self):
        self.active_kid.anwesend = True
        self.active_kid.zug_abreise = True
        self.active_kid.notiz_abreise = "Treffpunkt Westbahnhof"
        self.active_kid.top_jugendticket = False
        self.active_kid.save()
        staying_kid = self.create_kid(
            turnus=self.turnus,
            index="T2-2",
            first_name="Bob",
            last_name="Staying",
            anwesend=False,
            zug_abreise=False,
            notiz_abreise="Abholung am BuDo",
            top_jugendticket=True,
        )
        self.other_kid.zug_abreise = True
        self.other_kid.notiz_abreise = "must stay private"
        self.other_kid.save()

        response = self.client.get(self.contract_url("train-departure"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "kids": [
                {
                    "id": self.active_kid.id,
                    "full_name": "Ada Lovelace",
                    "present": True,
                    "train_departure": True,
                    "departure_note": "Treffpunkt Westbahnhof",
                    "youth_ticket": False,
                    "age": 14.0,
                    "registrant_name": "Grace Hopper",
                    "registrant_phone": "+4312345",
                    "siblings": "",
                },
                {
                    "id": staying_kid.id,
                    "full_name": "Bob Staying",
                    "present": False,
                    "train_departure": False,
                    "departure_note": "Abholung am BuDo",
                    "youth_ticket": True,
                    "age": 14.0,
                    "registrant_name": "Grace Hopper",
                    "registrant_phone": "+4312345",
                    "siblings": "",
                },
            ],
            "totals": {"train_departure": 1},
        })

    def test_check_in_form_redirects_and_the_focused_contract_is_current(self):
        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/check_in/{self.active_kid.id}",
                "check_in_date": "2026-07-01",
                "ausweis": "on",
                "e_card": "on",
                "einverstaendnis_erklaerung": "on",
                "notiz": "",
                "amount": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "ok": True,
            "redirect": f"/kid_details/{self.active_kid.id}",
        })
        refreshed = self.client.get(
            self.contract_url("check-in", self.active_kid),
        )
        self.assertTrue(refreshed.json()["kid"]["present"])
        self.assertTrue(refreshed.json()["kid"]["id_card"])

    def test_check_out_form_redirects_and_the_focused_contract_is_current(self):
        self.active_kid.anwesend = True
        self.active_kid.e_card = True
        self.active_kid.ausweis = True
        self.active_kid.save()

        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/check_out/{self.active_kid.id}",
                "early_abreise_date": "2026-07-14",
                "notiz": "",
                "amount": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "ok": True,
            "redirect": f"/kid_details/{self.active_kid.id}",
        })
        refreshed = self.client.get(
            self.contract_url("check-out", self.active_kid),
        )
        self.assertFalse(refreshed.json()["kid"]["present"])
        self.assertFalse(refreshed.json()["kid"]["e_card"])
        self.assertFalse(refreshed.json()["kid"]["id_card"])

    def test_train_writes_refresh_state_and_totals_in_the_focused_contract(self):
        self.active_kid.zug_abreise = False
        self.active_kid.save()

        toggle_response = self.client.post(
            reverse("toggle_zug_abreise"),
            {"id": self.active_kid.id},
        )
        note_response = self.client.post(
            reverse("update_notiz_abreise"),
            data=json.dumps({
                "id": self.active_kid.id,
                "notiz_abreise": "Treffpunkt Westbahnhof",
            }),
            content_type="application/json",
        )
        refreshed = self.client.get(self.contract_url("train-departure"))

        self.assertEqual(toggle_response.status_code, 200)
        self.assertEqual(toggle_response.json()["new_count"], 1)
        self.assertEqual(note_response.status_code, 200)
        self.assertEqual(refreshed.json()["totals"]["train_departure"], 1)
        self.assertTrue(refreshed.json()["kids"][0]["train_departure"])
        self.assertEqual(
            refreshed.json()["kids"][0]["departure_note"],
            "Treffpunkt Westbahnhof",
        )

    def test_cross_turnus_attendance_and_transport_writes_are_rejected(self):
        attendance_response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/check_in/{self.other_kid.id}",
                "check_in_date": "2026-08-01",
            },
        )
        toggle_response = self.client.post(
            reverse("toggle_zug_abreise"),
            {"id": self.other_kid.id},
        )
        note_response = self.client.post(
            reverse("update_notiz_abreise"),
            data=json.dumps({
                "id": self.other_kid.id,
                "notiz_abreise": "must not save",
            }),
            content_type="application/json",
        )

        self.assertEqual(attendance_response.status_code, 404)
        self.assertEqual(toggle_response.status_code, 404)
        self.assertEqual(note_response.status_code, 404)
        self.other_kid.refresh_from_db()
        self.assertIsNone(self.other_kid.anwesend)
        self.assertIsNone(self.other_kid.zug_abreise)
        self.assertEqual(self.other_kid.notiz_abreise, "")

    def test_write_interfaces_enforce_csrf_and_accept_the_bootstrap_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        denied = csrf_client.post(
            reverse("toggle_zug_abreise"),
            {"id": self.active_kid.id},
        )
        token = csrf_client.get(reverse("bootstrap-api")).json()["csrf_token"]
        accepted = csrf_client.post(
            reverse("toggle_zug_abreise"),
            {"id": self.active_kid.id},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 200)


@override_settings(STORAGES=TEST_STORAGES)
class AttendanceContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="attendance-performance",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contract(self, key, kid=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        if kid:
            url = f"{url}?id={kid.id}"
        return measure_http_get(self.client, url)

    def test_query_growth_is_bounded_and_payloads_beat_the_legacy_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        selected_kid = Kinder.objects.filter(turnus=self.turnus).first()
        small = {
            "check-in": self.measure_contract("check-in", selected_kid),
            "check-out": self.measure_contract("check-out", selected_kid),
            "train-arrival": self.measure_contract("train-arrival"),
            "train-departure": self.measure_contract("train-departure"),
        }

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = {
            "check-in": self.measure_contract("check-in", selected_kid),
            "check-out": self.measure_contract("check-out", selected_kid),
            "train-arrival": self.measure_contract("train-arrival"),
            "train-departure": self.measure_contract("train-departure"),
        }

        for key in small:
            with self.subTest(contract=key):
                self.assertEqual(small[key].status_code, 200)
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 8)
                self.assertQueryGrowthAtMost(
                    small[key],
                    realistic[key],
                    1,
                )
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
