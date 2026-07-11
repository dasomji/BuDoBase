from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import GeldForm
from .models import Auslagerorte, Geld, Kinder, Profil, Schwerpunkte, Schwerpunktzeit, Turnus


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


class PocketMoneyFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("money-user", password="secret")
        self.turnus = Turnus.objects.create(turnus_nr=3, turnus_beginn=date(2026, 7, 1))
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.kid = Kinder.objects.create(
            kid_index="T3-1",
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
        self.client.force_login(self.user)

    def test_pocket_money_form_rejects_negative_input(self):
        self.assertFalse(GeldForm({"amount": -5}).is_valid())

    def test_kid_detail_buttons_apply_the_transaction_sign(self):
        for action, expected in (("withdraw", -5), ("topup", 5)):
            response = self.client.post(
                reverse("form-submit-api"),
                {"_target": f"/kid_details/{self.kid.id}", "amount": 5, "money_action": action},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Geld.objects.latest("id").amount, expected)

    def test_checkout_subtracts_returned_money_from_a_positive_balance(self):
        Geld.objects.create(kinder=self.kid, added_by=self.user, amount=12.5)

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": 12.5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.kid.get_taschengeld_sum(), 0)

    def test_checkout_adds_money_paid_toward_a_negative_balance(self):
        Geld.objects.create(kinder=self.kid, added_by=self.user, amount=-3)

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.kid.get_taschengeld_sum(), -1)

    def test_checkout_rejects_a_negative_amount_without_checking_out(self):
        self.kid.anwesend = True
        self.kid.save()

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": -2},
        )

        self.assertEqual(response.status_code, 422)
        self.kid.refresh_from_db()
        self.assertTrue(self.kid.anwesend)
