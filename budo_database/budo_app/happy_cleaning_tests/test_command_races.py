import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase
from django.urls import reverse

from budo_app.models import HappyCleaning, HappyCleaningStation, Turnus


@skipUnless(
    connection.vendor == "postgresql",
    "Row-locking command races require PostgreSQL.",
)
class HappyCleaningManagementRaceTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.users = []
        for index in range(2):
            user = User.objects.create_user(username=f"race-editor-{index}")
            user.profil.turnus = self.turnus
            user.profil.save(update_fields=["turnus"])
            self.users.append(user)

    def concurrent_posts(self, url, payloads):
        barrier = Barrier(2)

        def post(index):
            close_old_connections()
            try:
                client = Client()
                client.force_login(self.users[index])
                barrier.wait(timeout=10)
                response = client.post(
                    url,
                    data=json.dumps(payloads[index]),
                    content_type="application/json",
                )
                return response.status_code, response.json()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(post, range(2)))

    def test_concurrent_event_create_allocates_distinct_contiguous_numbers(self):
        results = self.concurrent_posts(
            reverse("happy-cleaning-event-create-api"),
            [
                {"request_id": "race-create-a"},
                {"request_id": "race-create-b"},
            ],
        )

        self.assertEqual([status for status, _payload in results], [201, 201])
        self.assertEqual(
            list(HappyCleaning.objects.values_list("display_number", flat=True)),
            [1, 2],
        )

    def test_concurrent_station_reorders_accept_only_one_expected_revision(self):
        event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=1,
        )
        stations = [
            HappyCleaningStation.objects.create(
                happy_cleaning=event,
                name=name,
                max_kids=2,
                meeting_point="Treffpunkt",
                position=position,
            )
            for position, name in enumerate(("A", "B", "C"), start=1)
        ]
        results = self.concurrent_posts(
            reverse("happy-cleaning-station-reorder-api", args=[event.id]),
            [
                {
                    "request_id": "race-order-a",
                    "expected_revision": 1,
                    "station_ids": [stations[2].id, stations[1].id, stations[0].id],
                },
                {
                    "request_id": "race-order-b",
                    "expected_revision": 1,
                    "station_ids": [stations[1].id, stations[0].id, stations[2].id],
                },
            ],
        )

        self.assertCountEqual(
            [status for status, _payload in results],
            [200, 409],
        )
        self.assertEqual(
            [payload.get("code") for _status, payload in results].count("stale"),
            1,
        )
        self.assertEqual(
            list(HappyCleaningStation.objects.filter(
                happy_cleaning=event,
            ).values_list("position", flat=True)),
            [1, 2, 3],
        )
