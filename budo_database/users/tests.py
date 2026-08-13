from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from budo_app.models import TurnusMembership


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
