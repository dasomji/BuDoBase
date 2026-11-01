from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from budo_app.models import TurnusMembership


class AnonymousFormCsrfTests(TestCase):
    def test_login_and_registration_adapter_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for target in ("/login/", "/register/"):
            with self.subTest(target=target):
                response = client.post("/api/form-submit/", {"_target": target})
                self.assertEqual(response.status_code, 403)

    def test_anonymous_login_adapter_accepts_bootstrap_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/bootstrap/").json()["csrf_token"]
        response = client.post(
            "/api/form-submit/", {"_target": "/login/"}, HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 422)


@override_settings(REGISTRATION_PASSPHRASE="legacy-shared-secret")
class PublicRegistrationTests(TestCase):
    def test_signup_without_shared_passphrase_enters_awaiting_dashboard(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-teamer",
                "email": "new-teamer@example.com",
                "password1": "A-safe-password-189!",
                "password2": "A-safe-password-189!",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )
        user = User.objects.get(username="new-teamer")
        self.assertFalse(TurnusMembership.objects.filter(user=user).exists())

    def test_email_is_required_and_normalized_server_side(self):
        missing = self.client.post(
            reverse("register"),
            {
                "username": "missing-email",
                "password1": "A-safe-password-189!",
                "password2": "A-safe-password-189!",
            },
        )
        self.assertEqual(missing.status_code, 200)
        self.assertFalse(User.objects.filter(username="missing-email").exists())

        response = self.client.post(
            reverse("register"),
            {
                "username": "normalized-email",
                "email": "  New.Teamer@EXAMPLE.COM  ",
                "password1": "A-safe-password-189!",
                "password2": "A-safe-password-189!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            User.objects.get(username="normalized-email").email,
            "new.teamer@example.com",
        )

    def test_email_must_be_case_insensitively_unique(self):
        User.objects.create_user(
            username="existing-teamer",
            email="existing@example.com",
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "duplicate-email",
                "email": "EXISTING@EXAMPLE.COM",
                "password1": "A-safe-password-189!",
                "password2": "A-safe-password-189!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="duplicate-email").exists())

    def test_database_rejects_case_variant_nonblank_duplicate_email(self):
        User.objects.create_user(
            username="database-email-owner",
            email="database@example.com",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="database-email-duplicate",
                email="DATABASE@EXAMPLE.COM",
            )
