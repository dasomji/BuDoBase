from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import create_first_aid_entry_for_test
from budo_app.memberships import create_membership, select_turnus
from budo_app.models import (
    ErsteHilfeEintrag,
    Geld,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Notizen,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)
from budo_app.read_contract_tests.fixtures import ActiveTurnusFixtureFactory
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
)


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class KidsContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kids-performance-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def contract_url(self, key, **params):
        base = reverse("route-data-api", kwargs={"contract_key": key})
        if not params:
            return base
        query = "&".join(f"{name}={value}" for name, value in params.items())
        return f"{base}?{query}"

    def create_ordinary_dynamic_detail(self, kid):
        events = [
            HappyCleaning.objects.create(
                turnus=self.turnus,
                display_number=number,
            )
            for number in (1, 2)
        ]
        stations = []
        for event, station_count in zip(events, (2, 1)):
            for position in range(1, station_count + 1):
                stations.append(
                    HappyCleaningStation.objects.create(
                        happy_cleaning=event,
                        name=f"Detail Ordinary {event.display_number}-{position}",
                        max_kids=8,
                        meeting_point="Hof",
                        position=position,
                    )
                )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=events[0],
            station=stations[0],
            child=kid,
        )
        return events, stations

    def grow_dynamic_detail(self, kid, events, stations):
        periods = list(
            self.turnus.schwerpunktzeit_set.order_by("swp_beginn", "id")
        )
        focuses = list(kid.schwerpunkte.all())
        for index, code in enumerate(("x1", "x2"), start=1):
            period = Schwerpunktzeit.objects.create(
                turnus=self.turnus,
                woche=code,
                swp_beginn=self.turnus.turnus_beginn + timedelta(days=12 + index),
                dauer=index,
            )
            periods.append(period)
            for focus_index in range(2):
                focus = Schwerpunkte.objects.create(
                    swp_name=f"Detail {code} Focus {focus_index}",
                    schwerpunktzeit=period,
                )
                focuses.append(focus)
                kid.schwerpunkte.add(focus)

        for number in range(3, 13):
            events.append(
                HappyCleaning.objects.create(
                    turnus=self.turnus,
                    display_number=number,
                )
            )
        selected_station_ids = {
            assignment.station_id
            for assignment in HappyCleaningAssignment.objects.filter(
                child=kid,
            )
        }
        for event in events:
            existing = list(event.stations.order_by("position", "id"))
            for position in range(len(existing) + 1, 6):
                station = HappyCleaningStation.objects.create(
                    happy_cleaning=event,
                    name=f"Detail Expanded {event.display_number}-{position}",
                    max_kids=8,
                    meeting_point="Hof",
                    position=position,
                )
                stations.append(station)
                existing.append(station)
            if not HappyCleaningAssignment.objects.filter(
                happy_cleaning=event,
                child=kid,
            ).exists():
                assignment = HappyCleaningAssignment.objects.create(
                    happy_cleaning=event,
                    station=existing[0],
                    child=kid,
                )
                selected_station_ids.add(assignment.station_id)
        return periods, focuses, selected_station_ids

    def test_directory_queries_stay_bounded_and_payload_beats_the_legacy_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = measure_http_get(
            self.client,
            self.contract_url("kids-directory"),
        )

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(
            self.client,
            self.contract_url("kids-directory"),
        )

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(realistic.response.json()["kids"]), 48)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
        self.assertQueryCountAtMost(realistic, 10)
        self.assertQueryGrowthAtMost(small, realistic, 1)

    def test_detail_queries_stay_bounded_as_kinder_and_histories_grow(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        kid = Kinder.objects.filter(turnus=self.turnus).order_by("id").first()
        events, stations = self.create_ordinary_dynamic_detail(kid)
        small = measure_http_get(
            self.client,
            self.contract_url("kid-detail", id=kid.id),
        )

        for index in range(40):
            Notizen.objects.create(
                kinder=kid,
                notiz=f"Zusätzliche Notiz {index}",
                added_by=self.user,
            )
            create_first_aid_entry_for_test(
                kinder=kid,
                beschreibung=f"Zusätzlicher EH-Eintrag {index}",
                added_by=self.user,
            )
            Geld.objects.create(
                kinder=kid,
                amount=-1,
                added_by=self.user,
            )
        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        periods, focuses, selected_station_ids = self.grow_dynamic_detail(
            kid,
            events,
            stations,
        )
        expected_note_ids = set(
            kid.notizen.values_list("id", flat=True)
        )
        expected_first_aid_ids = set(
            kid.erste_hilfe_eintraege.values_list("id", flat=True)
        )
        expected_transaction_ids = set(
            kid.geld.values_list("id", flat=True)
        )

        realistic = measure_http_get(
            self.client,
            self.contract_url("kid-detail", id=kid.id),
        )

        payload = realistic.response.json()["kids"][0]
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(payload["notes"]), 42)
        self.assertEqual(len(payload["first_aid_entries"]), 42)
        self.assertEqual(len(payload["transactions"]), 42)
        self.assertEqual(
            {note["id"] for note in payload["notes"]},
            expected_note_ids,
        )
        self.assertEqual(
            {entry["id"] for entry in payload["first_aid_entries"]},
            expected_first_aid_ids,
        )
        self.assertEqual(
            {transaction["id"] for transaction in payload["transactions"]},
            expected_transaction_ids,
        )
        self.assertEqual(
            [period["period_id"] for period in payload["focus_assignments"]],
            [
                period.id
                for period in sorted(
                    periods,
                    key=lambda period: (period.swp_beginn, period.id),
                )
            ],
        )
        self.assertEqual(
            {
                focus["id"]
                for period in payload["focus_assignments"]
                for focus in period["focuses"]
            },
            {focus.id for focus in focuses},
        )
        self.assertEqual(
            [event["event_id"] for event in payload["happy_cleaning_assignments"]],
            [event.id for event in events],
        )
        self.assertEqual(
            {
                event["target"].get("station_id")
                for event in payload["happy_cleaning_assignments"]
                if event["target"]["kind"] == "station"
            },
            selected_station_ids,
        )
        self.assertEqual(len(periods), 4)
        self.assertEqual(len(events), 12)
        self.assertEqual(len(stations), 60)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
        self.assertQueryCountAtMost(realistic, 15)
        self.assertQueryGrowthAtMost(small, realistic, 1)
