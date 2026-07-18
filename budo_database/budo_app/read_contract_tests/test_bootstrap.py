from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import (
    Auslagerorte,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)


class BootstrapContractTests(TestCase):
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
            username="bootstrap-user",
            password="secret",
            email="bootstrap@example.test",
        )
        self.user.profil.rufname = "Bootstrap Teamer"
        self.user.profil.turnus = self.turnus
        self.user.profil.save()

        self.active_kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Änne",
            kid_nachname="Österreich",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=False,
        )
        Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Turnus",
            kid_birthday=date(2012, 8, 2),
            turnus=self.other_turnus,
        )
        focus_time = Schwerpunktzeit.objects.get(turnus=self.turnus, woche="w1")
        self.focus = Schwerpunkte.objects.create(
            swp_name="Überleben",
            schwerpunktzeit=focus_time,
        )
        other_focus_time = Schwerpunktzeit.objects.get(
            turnus=self.other_turnus,
            woche="w1",
        )
        Schwerpunkte.objects.create(
            swp_name="Other Focus",
            schwerpunktzeit=other_focus_time,
        )
        self.place = Auslagerorte.objects.create(name="Ötscher Hütte")

    def test_public_bootstrap_returns_only_public_shell_state(self):
        response = self.client.get(reverse("bootstrap-api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"authenticated", "csrf_token", "messages"})
        self.assertFalse(payload["authenticated"])
        self.assertTrue(payload["csrf_token"])
        self.assertEqual(payload["messages"], [])

    def test_authenticated_bootstrap_returns_minimal_active_shell_and_search(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("bootstrap-api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"], {
            "id": self.user.profil.id,
            "username": "bootstrap-user",
            "rufname": "Bootstrap Teamer",
        })
        self.assertEqual(payload["turnus"], {
            "id": self.turnus.id,
            "label": str(self.turnus),
            "number": 2,
            "start": "2026-07-01",
            "end": "2026-07-14",
        })
        self.assertEqual(payload["search_index"], {
            "kids": [{
                "id": self.active_kid.id,
                "full_name": "Änne Österreich",
                "present": False,
            }],
            "focuses": [{"id": self.focus.id, "name": "Überleben"}],
            "places": [{"id": self.place.id, "name": "Ötscher Hütte"}],
        })
        self.assertEqual(
            set(payload["permissions"]),
            {
                "change_kids", "change_profiles", "change_focuses",
                "change_places", "view_auditevent", "export_auditevent",
            },
        )
        for unrelated in ("team", "focus_times", "totals", "activity", "turnuses"):
            self.assertNotIn(unrelated, payload)

    def test_only_bootstrap_consumes_each_queued_message_once(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profil"),
            {
                "rufname": "Bootstrap Teamer",
                "allergien": "",
                "coffee": "",
                "rolle": "b",
                "essen": "ft",
                "telefonnummer": "",
                "turnus": self.turnus.id,
            },
        )
        self.assertEqual(response.status_code, 302)

        route_response = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "kids-directory"},
            )
        )
        first_bootstrap = self.client.get(reverse("bootstrap-api"))
        second_bootstrap = self.client.get(reverse("bootstrap-api"))

        self.assertEqual(route_response.status_code, 200)
        self.assertNotIn("messages", route_response.json())
        self.assertEqual(first_bootstrap.json()["messages"], [
            {"text": "Profil upgedatet!", "tags": "success"},
        ])
        self.assertEqual(second_bootstrap.json()["messages"], [])
