from django.test import TestCase, override_settings
from django.urls import reverse


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
