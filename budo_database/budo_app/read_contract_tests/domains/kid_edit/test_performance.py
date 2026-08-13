from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Schwerpunktzeit,
    Turnus,
)
from budo_app.read_contracts.measurement import (
    QueryBudgetAssertions,
    measure_http_get,
)


class KidEditContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=163,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kid-edit-performance-user",
            password="secret",
        )
        approve_and_select_turnus(self.user.profil.user, self.turnus)
        self.user.profil.save()
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.kid = Kinder.objects.create(
            kid_index="PERF-163-07",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            happy_cleaning_number=17,
        )
        self.other_kid = Kinder.objects.create(
            kid_index="PERF-163-07-OTHER",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
        )
        self.periods = list(
            self.turnus.schwerpunktzeit_set.order_by("swp_beginn", "id")
        )
        self.focuses = []
        for index, period in enumerate(self.periods):
            focus = Schwerpunkte.objects.create(
                swp_name=f"Ordinary Focus {index}",
                schwerpunktzeit=period,
            )
            self.focuses.append(focus)
            self.kid.schwerpunkte.add(focus)

        self.events = [
            HappyCleaning.objects.create(
                turnus=self.turnus,
                display_number=number,
            )
            for number in (1, 2)
        ]
        self.stations = []
        for event, station_count in zip(self.events, (2, 1)):
            for position in range(1, station_count + 1):
                self.stations.append(
                    HappyCleaningStation.objects.create(
                        happy_cleaning=event,
                        name=f"Ordinary {event.display_number}-{position}",
                        max_kids=8,
                        meeting_point="Hof",
                        position=position,
                    )
                )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.events[0],
            station=self.stations[0],
            child=self.kid,
        )

    def contract_url(self):
        return (
            reverse("route-data-api", kwargs={"contract_key": "kid-edit"})
            + f"?id={self.kid.id}"
        )

    def grow_to_realistic_dynamic_configuration(self):
        for index, code in enumerate(("x1", "x2"), start=1):
            period = Schwerpunktzeit.objects.create(
                turnus=self.turnus,
                woche=code,
                swp_beginn=self.turnus.turnus_beginn + timedelta(days=12 + index),
                dauer=index,
            )
            self.periods.append(period)
            for focus_index in range(2):
                focus = Schwerpunkte.objects.create(
                    swp_name=f"Expanded {code} Focus {focus_index}",
                    schwerpunktzeit=period,
                )
                self.focuses.append(focus)
                self.kid.schwerpunkte.add(focus)

        for number in range(3, 13):
            self.events.append(
                HappyCleaning.objects.create(
                    turnus=self.turnus,
                    display_number=number,
                )
            )

        stations_by_event = {
            event.id: list(event.stations.order_by("position", "id"))
            for event in self.events
        }
        for event in self.events:
            existing = stations_by_event[event.id]
            for position in range(len(existing) + 1, 6):
                station = HappyCleaningStation.objects.create(
                    happy_cleaning=event,
                    name=f"Expanded {event.display_number}-{position}",
                    max_kids=8,
                    meeting_point="Hof",
                    position=position,
                )
                self.stations.append(station)
                existing.append(station)
            if not HappyCleaningAssignment.objects.filter(
                happy_cleaning=event,
                child=self.kid,
            ).exists():
                HappyCleaningAssignment.objects.create(
                    happy_cleaning=event,
                    station=existing[0],
                    child=self.kid,
                )
            HappyCleaningAssignment.objects.create(
                happy_cleaning=event,
                station=existing[-1],
                child=self.other_kid,
            )

    def test_queries_stay_bounded_as_periods_events_and_stations_grow(self):
        ordinary = measure_http_get(self.client, self.contract_url())
        ordinary_kid = ordinary.response.json()["kid"]
        self.assertEqual(len(ordinary_kid["swp_periods"]), 2)
        self.assertEqual(len(ordinary_kid["happy_cleaning_events"]), 2)
        self.assertEqual(
            sum(
                option["target"]["kind"] == "station"
                for event in ordinary_kid["happy_cleaning_events"]
                for option in event["options"]
            ),
            3,
        )

        self.grow_to_realistic_dynamic_configuration()
        enlarged = measure_http_get(self.client, self.contract_url())

        self.assertEqual(ordinary.status_code, 200)
        self.assertEqual(enlarged.status_code, 200)
        kid = enlarged.response.json()["kid"]
        self.assertEqual(
            [period["id"] for period in kid["swp_periods"]],
            [
                period.id
                for period in sorted(
                    self.periods,
                    key=lambda period: (period.swp_beginn, period.id),
                )
            ],
        )
        self.assertEqual(
            {
                option["target"]["focus_id"]
                for period in kid["swp_periods"]
                for option in period["options"]
                if option["target"]["kind"] == "focus"
            },
            {focus.id for focus in self.focuses},
        )
        self.assertEqual(
            [event["id"] for event in kid["happy_cleaning_events"]],
            [event.id for event in self.events],
        )
        self.assertEqual(
            {
                option["target"]["station_id"]
                for event in kid["happy_cleaning_events"]
                for option in event["options"]
                if option["target"]["kind"] == "station"
            },
            {station.id for station in self.stations},
        )
        self.assertEqual(len(kid["swp_periods"]), 4)
        self.assertEqual(len(kid["happy_cleaning_events"]), 12)
        self.assertEqual(
            sum(
                option["target"]["kind"] == "station"
                for event in kid["happy_cleaning_events"]
                for option in event["options"]
            ),
            60,
        )
        self.assertQueryCountAtMost(enlarged, 12)
        self.assertQueryGrowthAtMost(ordinary, enlarged, 1)
