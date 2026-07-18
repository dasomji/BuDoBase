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


class HappyCleaningContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(
            username="happy-cleaning-reader",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=7,
            has_operational_activity=True,
        )
        self.empty_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=2,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=99,
        )
        self.user.profil.rufname = "Mira"
        self.user.profil.save(update_fields=["rufname"])
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=3,
            meeting_point="Vor dem Speisesaal",
            wishes="Fenster nicht vergessen",
            responsible_profile=self.user.profil,
            position=1,
            version=4,
        )
        self.empty_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Vor der Küche",
            position=2,
            version=2,
        )
        self.checked_todo = HappyCleaningTodo.objects.create(
            station=self.station,
            text="Tische wischen",
            position=1,
            checked=True,
            version=3,
        )
        self.open_todo = HappyCleaningTodo.objects.create(
            station=self.station,
            text="Boden kehren",
            position=2,
            version=1,
        )
        self.numbered_kid = Kinder.objects.create(
            kid_index="HC-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            anwesend=True,
            happy_cleaning_number=7,
            illness="Private Krankheit",
            anmelder_email="private@example.test",
            anmerkung="Private Notiz",
        )
        self.numberless_kid = Kinder.objects.create(
            kid_index="HC-2",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            anwesend=True,
            sozialversicherungsnr="private-number",
        )
        self.absent_kid = Kinder.objects.create(
            kid_index="HC-3",
            kid_vorname="Linus",
            kid_nachname="Torvalds",
            turnus=self.turnus,
            anwesend=False,
            wo="Sallingstadt",
            happy_cleaning_number=3,
        )
        self.numbered_assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.numbered_kid,
            version=6,
        )
        self.absent_assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.absent_kid,
            version=2,
        )
        self.other_kid = Kinder.objects.create(
            kid_index="OTHER-1",
            kid_vorname="Other",
            kid_nachname="Child",
            turnus=self.other_turnus,
            happy_cleaning_number=1,
        )
        self.other_profile = User.objects.create_user(
            username="other-happy-cleaning-reader",
        ).profil
        self.other_profile.rufname = "Other carer"
        self.other_profile.turnus = self.other_turnus
        self.other_profile.save(update_fields=["rufname", "turnus"])
        self.client.force_login(self.user)

    def url(self, key, **query):
        path = reverse("route-data-api", kwargs={"contract_key": key})
        if query:
            path += "?" + "&".join(
                f"{name}={value}" for name, value in query.items()
            )
        return path

    def test_overview_lists_only_active_turnus_events_with_revisions(self):
        response = self.client.get(self.url("happy-cleaning-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "events": [
                {
                    "id": self.event.id,
                    "display_number": 1,
                    "revision": 7,
                    "can_delete": False,
                },
                {
                    "id": self.empty_event.id,
                    "display_number": 2,
                    "revision": 2,
                    "can_delete": True,
                },
            ],
        })
        self.assertNotContains(response, "99")

    def test_assignment_snapshot_exposes_only_search_station_child_and_presence_fields(self):
        response = self.client.get(self.url(
            "happy-cleaning-assignment",
            event_id=self.event.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {"id": self.event.id, "display_number": 1, "revision": 7},
            "summary": {"assigned_present": 1, "present_total": 2},
            "children": [
                {
                    "id": self.numbered_kid.id,
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "full_name": "Ada Lovelace",
                    "number": 7,
                    "number_version": 1,
                    "present": True,
                    "absence_location": None,
                    "assigned_station": {
                        "id": self.station.id,
                        "name": "Speisesaal",
                    },
                    "assignment_version": 6,
                },
                {
                    "id": self.numberless_kid.id,
                    "first_name": "Grace",
                    "last_name": "Hopper",
                    "full_name": "Grace Hopper",
                    "number": None,
                    "number_version": 1,
                    "present": True,
                    "absence_location": None,
                    "assigned_station": None,
                    "assignment_version": None,
                },
                {
                    "id": self.absent_kid.id,
                    "first_name": "Linus",
                    "last_name": "Torvalds",
                    "full_name": "Linus Torvalds",
                    "number": 3,
                    "number_version": 1,
                    "present": False,
                    "absence_location": "Sallingstadt",
                    "assigned_station": {
                        "id": self.station.id,
                        "name": "Speisesaal",
                    },
                    "assignment_version": 2,
                },
            ],
            "stations": [
                {
                    "id": self.station.id,
                    "version": 4,
                    "name": "Speisesaal",
                    "wishes": "Fenster nicht vergessen",
                    "meeting_point": "Vor dem Speisesaal",
                    "responsible": {"id": self.user.profil.id, "name": "Mira"},
                    "max_kids": 3,
                    "assigned_count": 2,
                    "free_seats": 1,
                    "todo_progress_percentage": 50,
                    "children": [
                        {
                            "id": self.numbered_kid.id,
                            "full_name": "Ada Lovelace",
                            "short_name": "Ada Lo",
                            "present": True,
                            "assignment_version": 6,
                        },
                        {
                            "id": self.absent_kid.id,
                            "full_name": "Linus Torvalds",
                            "short_name": "Linus To",
                            "present": False,
                            "assignment_version": 2,
                        },
                    ],
                },
                {
                    "id": self.empty_station.id,
                    "version": 2,
                    "name": "Küche",
                    "wishes": "",
                    "meeting_point": "Vor der Küche",
                    "responsible": None,
                    "max_kids": 2,
                    "assigned_count": 0,
                    "free_seats": 2,
                    "todo_progress_percentage": None,
                    "children": [],
                },
            ],
        })
        payload = response.content.decode()
        for private_value in (
            "Private Krankheit",
            "private@example.test",
            "Private Notiz",
            "private-number",
            "Other Child",
        ):
            self.assertNotIn(private_value, payload)

    def test_event_contracts_hide_cross_turnus_ids_as_not_found(self):
        response = self.client.get(self.url(
            "happy-cleaning-assignment",
            event_id=self.other_event.id,
        ))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Other Child", status_code=404)

    def test_station_management_returns_editable_station_and_todo_projection(self):
        HappyCleaningStation.objects.filter(pk=self.empty_station.pk).update(
            responsible_profile=self.other_profile,
        )

        response = self.client.get(self.url(
            "happy-cleaning-stations",
            event_id=self.event.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {"id": self.event.id, "display_number": 1, "revision": 7},
            "responsible_profiles": [
                {"id": self.user.profil.id, "name": "Mira"},
            ],
            "copy_sources": [],
            "stations": [
                {
                    "id": self.station.id,
                    "version": 4,
                    "name": "Speisesaal",
                    "max_kids": 3,
                    "meeting_point": "Vor dem Speisesaal",
                    "wishes": "Fenster nicht vergessen",
                    "responsible_profile_id": self.user.profil.id,
                    "position": 1,
                    "has_ever_had_assignment": True,
                    "todo_progress_percentage": 50,
                    "todos": [
                        {
                            "id": self.checked_todo.id,
                            "text": "Tische wischen",
                            "position": 1,
                            "checked": True,
                            "version": 3,
                        },
                        {
                            "id": self.open_todo.id,
                            "text": "Boden kehren",
                            "position": 2,
                            "checked": False,
                            "version": 1,
                        },
                    ],
                },
                {
                    "id": self.empty_station.id,
                    "version": 2,
                    "name": "Küche",
                    "max_kids": 2,
                    "meeting_point": "Vor der Küche",
                    "wishes": "",
                    "responsible_profile_id": None,
                    "position": 2,
                    "has_ever_had_assignment": False,
                    "todo_progress_percentage": None,
                    "todos": [],
                },
            ],
        })
        self.assertNotContains(response, "Other carer")

    def test_station_detail_returns_operational_fields_with_versions(self):
        HappyCleaningAssignment.objects.bulk_create([
            HappyCleaningAssignment(
                happy_cleaning=self.event,
                station=self.station,
                child=self.other_kid,
                version=42,
            ),
        ])

        response = self.client.get(self.url(
            "happy-cleaning-station-detail",
            event_id=self.event.id,
            station_id=self.station.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {"id": self.event.id, "display_number": 1, "revision": 7},
            "station": {
                "id": self.station.id,
                "version": 4,
                "name": "Speisesaal",
                "meeting_point": "Vor dem Speisesaal",
                "wishes": "Fenster nicht vergessen",
                "responsible": {"id": self.user.profil.id, "name": "Mira"},
                "todo_progress_percentage": 50,
                "children": [
                    {
                        "id": self.numbered_kid.id,
                        "full_name": "Ada Lovelace",
                        "assignment_version": 6,
                    },
                    {
                        "id": self.absent_kid.id,
                        "full_name": "Linus Torvalds",
                        "assignment_version": 2,
                    },
                ],
                "todos": [
                    {
                        "id": self.checked_todo.id,
                        "text": "Tische wischen",
                        "position": 1,
                        "checked": True,
                        "version": 3,
                    },
                    {
                        "id": self.open_todo.id,
                        "text": "Boden kehren",
                        "position": 2,
                        "checked": False,
                        "version": 1,
                    },
                ],
            },
        })
        self.assertNotContains(response, "Other Child")
        self.assertNotContains(response, "Private Krankheit")

    def test_station_detail_hides_station_ids_outside_the_event(self):
        other_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="Other station",
            max_kids=3,
            meeting_point="Elsewhere",
            position=1,
        )

        response = self.client.get(self.url(
            "happy-cleaning-station-detail",
            event_id=self.event.id,
            station_id=other_station.id,
        ))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Other station", status_code=404)

    def test_print_projection_separates_and_deterministically_orders_children(self):
        lower_number = Kinder.objects.create(
            kid_index="HC-4",
            kid_vorname="Zoe",
            kid_nachname="Alpha",
            turnus=self.turnus,
            anwesend=True,
            happy_cleaning_number=2,
        )
        first_numberless = Kinder.objects.create(
            kid_index="HC-5",
            kid_vorname="Aaron",
            kid_nachname="Zebra",
            turnus=self.turnus,
            anwesend=True,
        )
        first_absent = Kinder.objects.create(
            kid_index="HC-6",
            kid_vorname="Barbara",
            kid_nachname="Able",
            turnus=self.turnus,
            anwesend=False,
            wo="Krankenhaus",
            happy_cleaning_number=9,
        )

        response = self.client.get(self.url(
            "happy-cleaning-print",
            event_id=self.event.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {"id": self.event.id, "display_number": 1, "revision": 7},
            "present_numbered": [
                {"id": lower_number.id, "full_name": "Zoe Alpha", "number": 2},
                {"id": self.numbered_kid.id, "full_name": "Ada Lovelace", "number": 7},
            ],
            "present_numberless": [
                {"id": first_numberless.id, "full_name": "Aaron Zebra"},
                {"id": self.numberless_kid.id, "full_name": "Grace Hopper"},
            ],
            "absent": [
                {
                    "id": first_absent.id,
                    "full_name": "Barbara Able",
                    "number": 9,
                    "absence_location": "Krankenhaus",
                },
                {
                    "id": self.absent_kid.id,
                    "full_name": "Linus Torvalds",
                    "number": 3,
                    "absence_location": "Sallingstadt",
                },
            ],
        })
        self.assertNotContains(response, "Other Child")
