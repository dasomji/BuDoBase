from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import (
    HappyCleaning,
    HappyCleaningStation,
    Turnus,
)


class HappyCleaningStationDetailPageTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(username="station-detail-page")
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
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=3,
            meeting_point="Tür",
            position=1,
        )
        self.other_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="Private Station",
            max_kids=1,
            meeting_point="Privat",
            position=1,
        )
        self.client.force_login(self.user)

    def test_active_turnus_event_and_station_deep_link_renders_react_shell(self):
        response = self.client.get(reverse(
            "happy-cleaning-station-detail-page",
            args=(self.event.id, self.station.id),
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/frontend/app.js")

    def test_foreign_or_mismatched_immutable_ids_are_not_found_without_details(self):
        foreign = self.client.get(
            f"/happy-cleaning/{self.other_event.id}/stations/"
            f"{self.other_station.id}/",
        )
        mismatched = self.client.get(
            f"/happy-cleaning/{self.event.id}/stations/"
            f"{self.other_station.id}/",
        )

        for response in (foreign, mismatched):
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(b"Private Station", response.content)
