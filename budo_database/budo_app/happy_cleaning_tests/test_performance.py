from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    HappyCleaningTodo,
    Kinder,
    Turnus,
)
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
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
            current_todos = station.todos.count()
            for index in range(current_todos, todos_per_station):
                HappyCleaningTodo.objects.create(
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
            "happy-cleaning-stations": measure_http_get(
                self.client,
                self._url("happy-cleaning-stations", **event_query),
            ),
            "happy-cleaning-station-detail": measure_http_get(
                self.client,
                self._url(
                    "happy-cleaning-station-detail",
                    **event_query,
                    station_id=first_station.id,
                ),
            ),
            "happy-cleaning-print": measure_http_get(
                self.client,
                self._url("happy-cleaning-print", **event_query),
            ),
        }

    def test_query_growth_is_bounded_for_children_stations_and_todos(self):
        self._grow_to(kids=3, stations=2, todos_per_station=2)
        small = self._measurements()

        self._grow_to(kids=48, stations=12, todos_per_station=8)
        realistic = self._measurements()

        for key in realistic:
            with self.subTest(contract=key):
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 12)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 1)
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
