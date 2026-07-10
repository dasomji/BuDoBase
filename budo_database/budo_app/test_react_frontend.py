from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Auslagerorte, Kinder, Profil, Schwerpunkte, Schwerpunktzeit, Turnus


@override_settings(
    MIDDLEWARE=[
        middleware
        for middleware in __import__(
            "budo_database.settings", fromlist=["MIDDLEWARE"]
        ).MIDDLEWARE
        if middleware != "budo_app.middleware.ReactFrontendMiddleware"
    ]
)
class AppDataApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("react-user", password="secret")
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.profile = self.user.profil
        self.profile.rufname = "React Teamer"
        self.profile.turnus = self.turnus
        self.profile.save()
        self.place = Auslagerorte.objects.create(name="BuDo")
        focus_time = Schwerpunktzeit.objects.get(turnus=self.turnus, woche="w1")
        self.focus = Schwerpunkte.objects.create(
            swp_name="Theater",
            ort=self.place,
            schwerpunktzeit=focus_time,
        )
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            rechnungsadresse="Main street",
            rechnung_ort="Vienna",
            rechnung_land="Austria",
        )

    def test_public_bootstrap_does_not_leak_camp_data(self):
        response = self.client.get(reverse("app-data-api"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertNotIn("kids", response.json())

    def test_authenticated_bootstrap_serializes_active_turnus(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("app-data-api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["profile"]["rufname"], "React Teamer")
        self.assertEqual(payload["kids"][0]["full_name"], "Ada Lovelace")
        self.assertEqual(payload["focuses"][0]["name"], "Theater")
        self.assertEqual(payload["places"][0]["name"], "BuDo")


class ReactShellTests(TestCase):
    def test_template_page_is_replaced_by_react_mount(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, '<div id="root"></div>', html=True)
        self.assertContains(response, "/static/frontend/app.js")
        self.assertContains(response, 'id="legacy-print-root"')

    def test_api_response_is_not_replaced(self):
        response = self.client.get(reverse("app-data-api"))

        self.assertEqual(response["Content-Type"], "application/json")

    def test_invalid_html_form_response_stays_in_react(self):
        response = self.client.post(
            reverse("login"),
            {"username": "missing", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)


class FormSubmitApiTests(TestCase):
    def test_login_validation_is_returned_as_json(self):
        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/login/", "username": "missing", "password": "bad"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])
        self.assertTrue(response.json()["errors"])

    def test_login_success_returns_redirect_contract(self):
        User.objects.create_user("api-login", password="secret")

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/login/", "username": "api-login", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertIn("redirect", response.json())
