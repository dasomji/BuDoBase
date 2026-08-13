from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.happy_cleaning_tests.task_fixtures import CanonicalTask

from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Turnus,
)
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
    measure_http_post,
)


class HappyCleaningPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="happy-cleaning-performance",
            password="secret",
        )
        self.user.profil.rufname = "Performance carer"
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["rufname", "turnus"])
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=3,
        )
        self.client.force_login(self.user)

    def _url(self, key, **query):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        if query:
            url += "?" + "&".join(
                f"{name}={value}" for name, value in query.items()
            )
        return url

    def _grow_to(self, *, kids, stations, todos_per_station):
        current_stations = self.event.stations.count()
        for index in range(current_stations, stations):
            HappyCleaningStation.objects.create(
                happy_cleaning=self.event,
                name=f"Station {index:02d}",
                max_kids=100,
                meeting_point=f"Treffpunkt {index:02d}",
                wishes=f"Wunsch {index:02d}",
                responsible_profile=self.user.profil,
                position=index,
                version=index + 1,
            )
        station_rows = list(self.event.stations.all())
        for station in station_rows:
            current_todos = CanonicalTask.objects.filter(station=station).count()
            for index in range(current_todos, todos_per_station):
                CanonicalTask.objects.create(
                    station=station,
                    text=f"Aufgabe {station.position:02d}-{index:02d}",
                    position=index,
                    checked=index % 2 == 0,
                    version=index + 1,
                )
        current_kids = Kinder.objects.filter(turnus=self.turnus).count()
        for index in range(current_kids, kids):
            child = Kinder.objects.create(
                kid_index=f"PERF-{index:03d}",
                kid_vorname=f"Kind {index:03d}",
                kid_nachname="Performance",
                turnus=self.turnus,
                anwesend=index % 4 != 0,
                wo="Sallingstadt" if index % 4 == 0 else None,
                happy_cleaning_number=index + 1 if index % 3 else None,
            )
            HappyCleaningAssignment.objects.create(
                happy_cleaning=self.event,
                station=station_rows[index % len(station_rows)],
                child=child,
                version=index + 1,
            )

    def _measurements(self):
        first_station = self.event.stations.first()
        event_query = {"event_id": self.event.id}
        return {
            "happy-cleaning-overview": measure_http_get(
                self.client,
                self._url("happy-cleaning-overview"),
            ),
            "happy-cleaning-assignment": measure_http_get(
                self.client,
                self._url("happy-cleaning-assignment", **event_query),
            ),
            "happy-cleaning-overview-station": measure_http_get(
                self.client,
                self._url(
                    "happy-cleaning-overview-station",
                    **event_query,
                    station_id=first_station.id,
                ),
            ),
            "happy-cleaning-print": measure_http_get(
                self.client,
                self._url("happy-cleaning-print"),
            ),
            "happy-cleaning-todo-print": measure_http_get(
                self.client,
                self._url("happy-cleaning-todo-print", **event_query),
            ),
        }

    def test_query_growth_is_bounded_for_children_stations_and_todos(self):
        self._grow_to(kids=3, stations=2, todos_per_station=2)
        small = self._measurements()

        self._grow_to(kids=48, stations=12, todos_per_station=8)
        realistic = self._measurements()

        response_byte_budgets = {
            "happy-cleaning-overview": 32_000,
            "happy-cleaning-assignment": 64_000,
            "happy-cleaning-overview-station": 32_000,
            "happy-cleaning-print": 64_000,
            "happy-cleaning-todo-print": 64_000,
        }
        for key in realistic:
            with self.subTest(contract=key):
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 12)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 1)
                self.assertLess(
                    realistic[key].response_bytes,
                    min(
                        response_byte_budgets[key],
                        RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                    ),
                )

    def test_overview_initial_and_historical_year_have_bounded_queries_and_bytes(self):
        historical_turnus = Turnus.objects.create(
            turnus_nr=4,
            turnus_beginn=date(2025, 8, 1),
        )
        historical_event = HappyCleaning.objects.create(
            turnus=historical_turnus,
            display_number=1,
        )
        initial_small = measure_http_get(
            self.client,
            self._url("happy-cleaning-overview"),
        )
        for index in range(30):
            station = HappyCleaningStation.objects.create(
                happy_cleaning=historical_event,
                name=f"Historische Station {index:02d}",
                max_kids=12,
                meeting_point=f"Archiv {index:02d}",
                position=index,
            )
            for todo_index in range(5):
                CanonicalTask.objects.create(
                    station=station,
                    text=f"Historische Aufgabe {todo_index}",
                    position=todo_index,
                )

        initial_large = measure_http_get(
            self.client,
            self._url("happy-cleaning-overview"),
        )
        active_year = measure_http_get(
            self.client,
            self._url("happy-cleaning-overview", year=2026),
        )
        historical = measure_http_get(
            self.client,
            self._url("happy-cleaning-overview", year=2025),
        )

        # The active overview includes one bounded query for create-station
        # responsible-person choices.
        self.assertQueryCountAtMost(initial_small, 9)
        self.assertQueryCountAtMost(initial_large, 9)
        self.assertQueryCountAtMost(active_year, 9)
        self.assertQueryCountAtMost(historical, 8)
        self.assertQueryGrowthAtMost(initial_small, initial_large, 0)
        self.assertEqual(initial_small.response_bytes, initial_large.response_bytes)
        self.assertLess(initial_large.response_bytes, 24_000)
        self.assertLess(active_year.response_bytes, 24_000)
        self.assertLess(historical.response_bytes, 16_000)

    def test_copy_preview_and_commit_have_explicit_query_and_response_budgets(self):
        historical_turnus = Turnus.objects.create(
            turnus_nr=4,
            turnus_beginn=date(2025, 8, 1),
        )
        source = HappyCleaning.objects.create(
            turnus=historical_turnus,
            display_number=1,
        )
        source_station_ids = []
        for station_index in range(12):
            station = HappyCleaningStation.objects.create(
                happy_cleaning=source,
                name=f"Quelle {station_index:02d}",
                max_kids=12,
                meeting_point=f"Archiv {station_index:02d}",
                position=station_index,
            )
            source_station_ids.append(station.id)
            for task_index in range(8):
                CanonicalTask.objects.create(
                    station=station,
                    text=f"Aufgabe {station_index:02d}-{task_index:02d}",
                    position=task_index,
                )

        conflict_target = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
        )
        HappyCleaningStation.objects.create(
            happy_cleaning=conflict_target,
            name="Quelle 00 Nord",
            max_kids=4,
            position=1,
        )
        preview = measure_http_post(
            self.client,
            reverse(
                "happy-cleaning-station-copy-api",
                args=[conflict_target.id],
            ),
            {
                "request_id": "performance-copy-preview",
                "expected_revision": conflict_target.revision,
                "source_event_id": source.id,
                "station_ids": source_station_ids,
            },
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.response.json()["result"], "conflicts")
        # Includes the User/Turnus/Profile/Membership lifetime authorization
        # lock acquired before the preview is built.
        self.assertQueryCountAtMost(preview, 19)
        self.assertLess(preview.response_bytes, 8_000)

        commit_target = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=3,
        )
        commit = measure_http_post(
            self.client,
            reverse(
                "happy-cleaning-station-copy-api",
                args=[commit_target.id],
            ),
            {
                "request_id": "performance-copy-commit",
                "expected_revision": commit_target.revision,
                "source_event_id": source.id,
                "station_ids": source_station_ids,
            },
        )
        self.assertEqual(commit.status_code, 200)
        self.assertEqual(commit.response.json()["result"], "copied")
        # Writes scale with the number of stations/tasks copied; the bound is
        # intentionally sized for this representative 12 × 8 batch.
        self.assertQueryCountAtMost(commit, 90)
        self.assertLess(commit.response_bytes, 56_000)
        self.assertEqual(commit_target.stations.count(), 12)
