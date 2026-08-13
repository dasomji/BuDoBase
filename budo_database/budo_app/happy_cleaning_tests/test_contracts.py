from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.happy_cleaning_tests.task_fixtures import CanonicalTask
from budo_app.test_membership_fixtures import approve_and_select_turnus

from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
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
        approve_and_select_turnus(self.user, self.turnus)
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
        self.checked_todo = CanonicalTask.objects.create(
            station=self.station,
            text="Tische wischen",
            position=1,
            checked=True,
            version=3,
        )
        self.open_todo = CanonicalTask.objects.create(
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
        self.numberless_assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=None,
            target_kind=HappyCleaningAssignment.TargetKind.EXCUSED,
            child=self.numberless_kid,
            version=7,
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

    def test_overview_orders_all_turni_and_only_eager_loads_the_active_year(self):
        older_turnus = Turnus.objects.create(
            turnus_nr=4,
            turnus_beginn=date(2025, 8, 1),
        )
        earlier_same_year = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 6, 1),
        )
        oldest_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2024, 7, 1),
        )
        HappyCleaning.objects.create(
            turnus=earlier_same_year,
            display_number=1,
        )
        HappyCleaning.objects.create(
            turnus=oldest_turnus,
            display_number=1,
        )
        older_event = HappyCleaning.objects.create(
            turnus=older_turnus,
            display_number=1,
            revision=5,
        )
        historical_profile = User.objects.create_user(
            username="historical-happy-cleaning-carer",
        ).profil
        historical_profile.rufname = "Historical carer"
        historical_profile.turnus = older_turnus
        historical_profile.save(update_fields=["rufname", "turnus"])
        HappyCleaningStation.objects.create(
            happy_cleaning=older_event,
            name="Historische Küche",
            max_kids=9,
            meeting_point="Altbau",
            responsible_profile=historical_profile,
            position=1,
            content_document={
                "type": "doc",
                "content": [{
                    "type": "taskList",
                    "content": [
                        {"type": "taskItem", "attrs": {"id": 9001, "checked": False, "version": 1}, "content": [{"type": "paragraph", "content": []}]},
                        {"type": "taskItem", "attrs": {"id": 9002, "checked": True, "version": 1}, "content": [{"type": "paragraph", "content": []}]},
                    ],
                }],
            },
        )
        same_year_private_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="Other station",
            max_kids=4,
            meeting_point="Other meeting point",
            responsible_profile=self.other_profile,
            position=1,
        )
        response = self.client.get(self.url("happy-cleaning-overview"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["active_year"], 2026)
        self.assertEqual(
            [
                (target["id"], target["display_number"], target["revision"])
                for target in payload["copy_targets"]
            ],
            [
                (self.event.id, 1, self.event.revision),
                (self.empty_event.id, 2, self.empty_event.revision),
            ],
        )
        self.assertEqual([group["year"] for group in payload["years"]], [2026, 2025, 2024])
        active = payload["years"][0]
        self.assertTrue(active["loaded"])
        self.assertEqual(
            [turnus["id"] for turnus in active["turnuses"]],
            [self.turnus.id, self.other_turnus.id, earlier_same_year.id],
        )
        self.assertEqual(
            [event["display_number"] for event in active["turnuses"][0]["events"]],
            [1, 2],
        )
        self.assertEqual(
            active["turnuses"][0]["events"][0]["stations"][0],
            {
                "id": self.station.id,
                "name": "Speisesaal",
                "max_kids": 3,
                "meeting_point": "Vor dem Speisesaal",
                "responsible": {
                    "id": self.user.profil.id,
                    "name": "Mira",
                },
                "task_item_count": 2,
                "assigned_count": 2,
                "overbooked_count": 0,
            },
        )
        same_year_private = active["turnuses"][1]["events"][0]["stations"][0]
        self.assertEqual(same_year_private["id"], same_year_private_station.id)
        self.assertIsNone(same_year_private["responsible"])
        historical = payload["years"][1]
        self.assertFalse(historical["loaded"])
        self.assertNotIn("stations", historical["turnuses"][0]["events"][0])
        serialized = response.content.decode()
        self.assertNotIn("Historische Küche", serialized)
        self.assertNotIn("Other carer", serialized)
        self.assertNotIn("Historical carer", serialized)
        self.assertNotIn("Other Child", serialized)

        loaded = self.client.get(self.url("happy-cleaning-overview", year=2025))
        self.assertEqual(loaded.status_code, 200)
        loaded_payload = loaded.json()
        self.assertEqual([group["year"] for group in loaded_payload["years"]], [2025])
        self.assertTrue(loaded_payload["years"][0]["loaded"])
        station = loaded_payload["years"][0]["turnuses"][0]["events"][0]["stations"][0]
        self.assertEqual(station["name"], "Historische Küche")
        self.assertEqual(station["task_item_count"], 2)
        self.assertIsNone(station["responsible"])
        loaded_serialized = loaded.content.decode()
        self.assertNotIn("Other carer", loaded_serialized)
        self.assertNotIn("Historical carer", loaded_serialized)
        self.assertNotIn("Other Child", loaded_serialized)

    def test_todo_print_contract_returns_ordered_station_documents_without_people(self):
        response = self.client.get(self.url(
            "happy-cleaning-todo-print",
            event_id=self.event.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {
                "id": self.event.id,
                "display_number": self.event.display_number,
                "revision": self.event.revision,
            },
            "stations": [
                {
                    "id": self.station.id,
                    "name": "Speisesaal",
                    "document": self.station.content_document,
                },
                {
                    "id": self.empty_station.id,
                    "name": "Küche",
                    "document": self.empty_station.content_document,
                },
            ],
        })
        serialized = response.content.decode()
        self.assertNotIn("Mira", serialized)
        self.assertNotIn("Ada Lovelace", serialized)
        self.assertNotIn("Private Krankheit", serialized)

    def test_assignment_snapshot_exposes_only_search_station_child_and_presence_fields(self):
        response = self.client.get(self.url(
            "happy-cleaning-assignment",
            event_id=self.event.id,
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "event": {"id": self.event.id, "display_number": 1, "revision": 7},
            "summary": {"assigned_present": 2, "present_total": 2},
            "number_batch": {
                "available": True,
                "children": [
                    {
                        "id": self.numberless_kid.id,
                        "full_name": "Grace Hopper",
                        "number": 1,
                        "expected_version": 1,
                    },
                ],
            },
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
                    "assigned_station": {
                        "id": "excused",
                        "name": "Entschuldigt",
                        "is_excused": True,
                    },
                    "assignment_version": 7,
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
                    "overbooked_count": 0,
                    "todo_progress_percentage": 50,
                    "children": [
                        {
                            "id": self.numbered_kid.id,
                            "full_name": "Ada Lovelace",
                            "short_name": "Ada Lo",
                            "number": 7,
                            "present": True,
                            "assignment_version": 6,
                        },
                        {
                            "id": self.absent_kid.id,
                            "full_name": "Linus Torvalds",
                            "short_name": "Linus To",
                            "number": 3,
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
                    "overbooked_count": 0,
                    "todo_progress_percentage": None,
                    "children": [],
                },
                {
                    "id": "excused",
                    "name": "Entschuldigt",
                    "is_excused": True,
                    "children": [
                        {
                            "id": self.numberless_kid.id,
                            "full_name": "Grace Hopper",
                            "short_name": "Grace Ho",
                            "number": None,
                            "present": True,
                            "assignment_version": 7,
                        },
                    ],
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

    def test_retired_management_and_detail_pages_return_not_found(self):
        self.assertEqual(
            self.client.get(
                f"/happy-cleaning/{self.event.id}/stations/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"/happy-cleaning/{self.event.id}/stations/"
                f"{self.station.id}/"
            ).status_code,
            404,
        )
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
            "happy-cleaning-overview-station",
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
                "max_kids": 3,
                "meeting_point": "Vor dem Speisesaal",
                "wishes": "Fenster nicht vergessen",
                "has_ever_had_assignment": True,
                "assigned_count": 2,
                "overbooked_count": 0,
                "content": [{
                    "type": "task_list",
                    "items": [
                        {
                            "id": self.checked_todo.id,
                            "text": "Tische wischen",
                            "checked": True,
                            "version": 3,
                        },
                        {
                            "id": self.open_todo.id,
                            "text": "Boden kehren",
                            "checked": False,
                            "version": 1,
                        },
                    ],
                }],
                "document": self.station.content_document,
                "is_historical": False,
                "can_edit": True,
                "can_delete": False,
                "can_toggle_tasks": True,
                "responsible": {"id": self.user.profil.id, "name": "Mira"},
                "todo_checked_count": 1,
                "todo_total_count": 2,
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
            "responsible_profiles": [
                {"id": self.user.profil.id, "name": "Mira"},
            ],
            "copy_targets": [{
                "id": self.empty_event.id,
                "display_number": 2,
                "revision": 2,
                "label": "Happy Cleaning 2",
            }],
        })
        self.assertNotContains(response, "Other Child")
        self.assertNotContains(response, "Private Krankheit")

    def test_overbooked_count_is_exact_across_read_contracts(self):
        HappyCleaningStation.objects.filter(pk=self.station.pk).update(max_kids=1)

        assignment = self.client.get(self.url(
            "happy-cleaning-assignment",
            event_id=self.event.id,
        )).json()
        overview = self.client.get(self.url(
            "happy-cleaning-overview",
        )).json()
        detail = self.client.get(self.url(
            "happy-cleaning-overview-station",
            event_id=self.event.id,
            station_id=self.station.id,
        )).json()

        assignment_station = next(
            station for station in assignment["stations"]
            if station["id"] == self.station.id
        )
        overview_station = overview["years"][0]["turnuses"][0]["events"][0]["stations"][0]
        self.assertEqual(assignment_station["overbooked_count"], 1)
        self.assertEqual(assignment_station["free_seats"], 0)
        self.assertEqual(overview_station["overbooked_count"], 1)
        self.assertEqual(detail["station"]["overbooked_count"], 1)

    def test_historical_station_detail_redacts_people_from_response(self):
        historical_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2025, 7, 1),
        )
        historical_event = HappyCleaning.objects.create(
            turnus=historical_turnus,
            display_number=1,
        )
        historical_profile = User.objects.create_user(
            username="historical-carer",
        ).profil
        historical_profile.rufname = "Private Carer"
        historical_profile.turnus = historical_turnus
        historical_profile.save(update_fields=["rufname", "turnus"])
        historical_child = Kinder.objects.create(
            kid_index="HIST-1",
            kid_vorname="Private",
            kid_nachname="Child",
            turnus=historical_turnus,
        )
        historical_station = HappyCleaningStation.objects.create(
            happy_cleaning=historical_event,
            name="Historische Küche",
            max_kids=7,
            meeting_point="Altbau",
            wishes="Leise arbeiten",
            responsible_profile=historical_profile,
            position=1,
            content_document={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Fenster öffnen"}],
                    },
                    {
                        "type": "taskList",
                        "content": [{
                            "type": "taskItem",
                            "attrs": {"id": 901, "checked": True, "version": 2},
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Boden kehren"}],
                            }],
                        }],
                    },
                ],
            },
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=historical_event,
            station=historical_station,
            child=historical_child,
        )

        response = self.client.get(self.url(
            "happy-cleaning-overview-station",
            event_id=historical_event.id,
            station_id=historical_station.id,
        ))

        self.assertEqual(response.status_code, 200)
        station = response.json()["station"]
        self.assertEqual(station["content"], [
            {"type": "paragraph", "text": "Fenster öffnen"},
            {
                "type": "task_list",
                "items": [{
                    "id": 901,
                    "text": "Boden kehren",
                    "checked": True,
                    "version": 2,
                }],
            },
        ])
        self.assertEqual(station["todos"], [{
            "id": 901,
            "text": "Boden kehren",
            "checked": True,
            "version": 2,
            "position": 1,
        }])
        self.assertTrue(station["is_historical"])
        self.assertFalse(station["can_toggle_tasks"])
        self.assertNotIn("responsible", station)
        self.assertNotIn("children", station)
        self.assertEqual(response.json()["copy_targets"], [
            {
                "id": self.event.id,
                "display_number": 1,
                "revision": 7,
                "label": "Happy Cleaning 1",
            },
            {
                "id": self.empty_event.id,
                "display_number": 2,
                "revision": 2,
                "label": "Happy Cleaning 2",
            },
        ])
        serialized = response.content.decode()
        self.assertNotIn("Private Carer", serialized)
        self.assertNotIn("Private Child", serialized)

    def test_station_detail_hides_station_ids_outside_the_event(self):
        other_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="Other station",
            max_kids=3,
            meeting_point="Elsewhere",
            position=1,
        )

        response = self.client.get(self.url(
            "happy-cleaning-overview-station",
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

        response = self.client.get(self.url("happy-cleaning-print"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "number_batch_event_id": self.event.id,
            "number_batch": {"available": False, "children": []},
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
