from budo_app.test_membership_fixtures import approve_and_select_turnus
import json
from copy import deepcopy
from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse

from budo_app.happy_cleaning_tests.task_fixtures import CanonicalTask

from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningStation,
    Turnus,
)


class HappyCleaningStationCreateTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1, turnus_beginn=date(2026, 7, 1)
        )
        self.user = User.objects.create_user(username="station-creator")
        approve_and_select_turnus(self.user, self.turnus)
        self.user.profil.rufname = "Mira"
        self.user.profil.save()
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus, display_number=1
        )
        self.client.force_login(self.user)

    def payload(self, **overrides):
        return {
            "request_id": "create-station",
            "expected_revision": self.event.revision,
            "name": "Speisesaal",
            "max_kids": 4,
            "meeting_point": "Tür",
            "wishes": "Fenster",
            "responsible_profile_id": self.user.profil.id,
            "document": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Hinweis"}],
                    },
                    {
                        "type": "taskList",
                        "content": [{
                            "type": "taskItem",
                            "attrs": {
                                "id": None,
                                "checked": True,
                                "version": None,
                            },
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Tische"}],
                            }],
                        }],
                    },
                ],
            },
            **overrides,
        }

    def post(self, payload):
        return self.client.post(
            reverse("happy-cleaning-station-create-api", args=[self.event.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_valid_create_is_atomic_assigns_open_server_tasks_and_replays(self):
        response = self.post(self.payload())
        replay = self.post(self.payload())

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(replay.status_code, 200, replay.content)
        self.assertEqual(HappyCleaningStation.objects.count(), 1)
        station = HappyCleaningStation.objects.get()
        task = CanonicalTask.objects.filter(station=station).get()
        self.assertEqual((task.version, task.checked, task.text), (1, False, "Tische"))
        self.assertEqual(
            station.content_document["content"][1]["content"][0]["attrs"],
            {"id": task.id, "checked": False, "version": 1},
        )
        self.assertEqual(response.json()["station"]["document"], station.content_document)
        self.assertEqual(replay.json()["station"]["id"], station.id)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(
            AuditEvent.objects.filter(
                request_id="create-station",
                action="happy_cleaning.station.create",
                outcome="success",
            ).count(),
            1,
        )

    def test_invalid_document_or_foreign_responsible_rolls_back_without_success_audit(self):
        foreign_turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 8, 1)
        )
        foreign_user = User.objects.create_user(username="foreign-responsible")
        approve_and_select_turnus(foreign_user.profil.user, foreign_turnus)
        foreign_user.profil.save()

        malformed = self.post(self.payload(
            request_id="malformed-create",
            document={"type": "doc", "content": [{"type": "heading"}]},
        ))
        forbidden = self.post(self.payload(
            request_id="foreign-create",
            responsible_profile_id=foreign_user.profil.id,
        ))

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(forbidden.status_code, 404)
        self.assertEqual(HappyCleaningStation.objects.count(), 0)
        self.assertFalse(AuditEvent.objects.filter(outcome="success").exists())

    def test_audit_failure_rolls_back_station_document_and_tasks(self):
        with mock.patch(
            "budo_app.happy_cleaning_commands.record_audit_event",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self.post(self.payload(request_id="audit-failure"))

        self.assertEqual(HappyCleaningStation.objects.count(), 0)
        self.assertEqual(CanonicalTask.objects.count(), 0)


class HappyCleaningStationStructuralEditTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        self.user = User.objects.create_user(username="structural-editor")
        approve_and_select_turnus(self.user.profil.user, self.turnus)
        self.user.profil.save()
        self.event = HappyCleaning.objects.create(turnus=self.turnus, display_number=1)
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=4,
            meeting_point="Tür",
            wishes="",
            position=1,
        )
        self.first = CanonicalTask.objects.create(
            station=self.station, text="Tische", position=1, checked=False
        )
        self.second = CanonicalTask.objects.create(
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
        tasks = list(CanonicalTask.objects.filter(
            station=self.station
        ).order_by("position"))
        self.assertEqual(self.station.name, "Großer Speisesaal")
        self.assertEqual(self.second.checked, False)
        self.assertEqual(self.second.version, 5)
        self.assertFalse(CanonicalTask.objects.filter(pk=self.first.id).exists())
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
