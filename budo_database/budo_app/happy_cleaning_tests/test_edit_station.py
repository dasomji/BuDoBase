import json
from copy import deepcopy
from datetime import date

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse

from budo_app.models import HappyCleaning, HappyCleaningStation, HappyCleaningTodo, Turnus


class HappyCleaningStationStructuralEditTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        self.user = User.objects.create_user(username="structural-editor")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        self.event = HappyCleaning.objects.create(turnus=self.turnus, display_number=1)
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=4,
            meeting_point="Tür",
            wishes="",
            position=1,
        )
        self.first = HappyCleaningTodo.objects.create(
            station=self.station, text="Tische", position=1, checked=False
        )
        self.second = HappyCleaningTodo.objects.create(
            station=self.station, text="Boden", position=2, checked=True, version=3
        )
        self.client.force_login(self.user)

    def payload(self, document, **overrides):
        return {
            "request_id": "structural-edit",
            "expected_version": self.station.version,
            "name": "Großer Speisesaal",
            "max_kids": 4,
            "meeting_point": "Haupteingang",
            "wishes": "Fenster",
            "responsible_profile_id": None,
            "document": document,
            **overrides,
        }

    def post(self, payload):
        return self.client.post(
            reverse(
                "happy-cleaning-station-update-api",
                args=[self.event.id, self.station.id],
            ),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_atomic_edit_preserves_server_task_state_and_allocates_new_identity(self):
        reopened = self.client.post(
            reverse(
                "happy-cleaning-todo-reopen-api",
                args=[self.event.id, self.station.id, self.second.id],
            ),
            data=json.dumps({
                "request_id": "concurrent-reopen",
                "expected_version": self.second.version,
            }),
            content_type="application/json",
        )
        self.assertEqual(reopened.status_code, 200)
        document = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hinweis"}]},
                {
                    "type": "taskList",
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {
                                "id": self.second.id,
                                "checked": False,
                                "version": 1,
                            },
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Boden neu"}]}],
                        },
                        {
                            "type": "taskItem",
                            "attrs": {"id": None, "checked": True, "version": None},
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fenster"}]}],
                        },
                    ],
                },
            ],
        }

        response = self.post(self.payload(document))

        self.assertEqual(response.status_code, 200, response.content)
        self.station.refresh_from_db()
        self.second.refresh_from_db()
        tasks = list(self.station.todos.order_by("position"))
        self.assertEqual(self.station.name, "Großer Speisesaal")
        self.assertEqual(self.second.checked, False)
        self.assertEqual(self.second.version, 5)
        self.assertFalse(HappyCleaningTodo.objects.filter(pk=self.first.id).exists())
        self.assertEqual(tasks[1].text, "Fenster")
        self.assertFalse(tasks[1].checked)
        self.assertNotIn(self.first.id, [task.id for task in tasks])
        self.assertEqual(
            self.station.content_document["content"][1]["content"][0]["attrs"],
            {"id": self.second.id, "checked": False, "version": 5},
        )

    def test_historical_turnus_update_is_hidden_and_locked_station_cannot_delete(self):
        historical_turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2025, 7, 1)
        )
        historical_event = HappyCleaning.objects.create(
            turnus=historical_turnus, display_number=1
        )
        historical_station = HappyCleaningStation.objects.create(
            happy_cleaning=historical_event,
            name="Archiv",
            max_kids=2,
            meeting_point="Alt",
            position=1,
        )
        hidden = self.client.post(
            reverse(
                "happy-cleaning-station-update-api",
                args=[historical_event.id, historical_station.id],
            ),
            data=json.dumps(self.payload({"type": "doc", "content": []})),
            content_type="application/json",
        )
        self.station.has_ever_had_assignment = True
        self.station.save(update_fields=["has_ever_had_assignment"])
        locked_delete = self.client.post(
            reverse(
                "happy-cleaning-station-delete-api",
                args=[self.event.id, self.station.id],
            ),
            data=json.dumps({
                "request_id": "locked-delete",
                "expected_version": self.station.version,
            }),
            content_type="application/json",
        )

        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(locked_delete.status_code, 409)
        self.assertEqual(locked_delete.json()["code"], "station_locked")

    def test_stale_or_malformed_edit_changes_nothing_and_returns_current_version(self):
        original = deepcopy(self.station.content_document)
        malformed = {"type": "doc", "content": [{"type": "heading", "content": []}]}

        invalid = self.post(self.payload(malformed))
        stale = self.post(self.payload({"type": "doc", "content": []}, expected_version=99))

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["current_version"], self.station.version)
        self.station.refresh_from_db()
        self.assertEqual(self.station.content_document, original)
        self.assertEqual(self.station.name, "Speisesaal")
