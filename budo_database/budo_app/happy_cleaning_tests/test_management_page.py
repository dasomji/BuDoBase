from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import HappyCleaning, Turnus


class HappyCleaningManagementPageTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(username="management-page")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
        )

    def test_active_turnus_deep_link_renders_the_react_shell(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse(
            "happy-cleaning-stations-page",
            args=(self.event.id,),
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/frontend/app.js")

    def test_deep_link_requires_authentication(self):
        response = self.client.get(
            f"/happy-cleaning/{self.event.id}/stations/",
        )

        self.assertEqual(response.status_code, 302)

    def test_foreign_turnus_deep_link_is_not_found_without_event_details(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/happy-cleaning/{self.other_event.id}/stations/",
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(str(self.other_turnus).encode(), response.content)
