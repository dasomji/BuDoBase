from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AdminTeamOverviewAuthorizationTests(TestCase):
    def test_django_staff_without_superuser_authority_cannot_read_global_teams(self):
        staff_user = User.objects.create_user(
            username="django-staff-only",
            is_staff=True,
            is_superuser=False,
        )
        self.client.force_login(staff_user)

        response = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "admin-team-overview"},
            )
        )

        self.assertEqual(response.status_code, 403)
