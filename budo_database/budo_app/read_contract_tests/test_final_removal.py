from django.contrib.auth.models import User
from django.test import TestCase


class LegacyAppDataRemovalTests(TestCase):
    def test_legacy_combined_application_data_url_is_removed(self):
        public_response = self.client.get("/api/app-data/")

        user = User.objects.create_user("removed-app-data", password="secret")
        self.client.force_login(user)
        authenticated_response = self.client.get("/api/app-data/")

        self.assertEqual(public_response.status_code, 404)
        self.assertEqual(authenticated_response.status_code, 404)
