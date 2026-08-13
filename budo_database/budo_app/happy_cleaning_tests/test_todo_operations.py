import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TransactionTestCase, override_settings
from django.urls import include, path, reverse

from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.happy_cleaning_station_documents import project_tasks
from budo_app.happy_cleaning_tests.task_fixtures import CanonicalTask

from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Turnus,
)
from budo_app.read_contracts.views import route_data
from budo_app.test_membership_fixtures import approve_and_select_turnus


urlpatterns = [
    path(
        "api/route-data/<slug:contract_key>/",
        route_data,
        name="route-data-api",
    ),
    path(
        "api/happy-cleaning/",
        include("budo_app.happy_cleaning_todo_urls"),
    ),
]


@override_settings(ROOT_URLCONF=__name__)
class CanonicalTaskOperationTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="todo-operator")
        profile = approve_and_select_turnus(self.user, self.turnus)
        profile.rufname = "Mira"
        profile.save(update_fields=("rufname",))
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=4,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=4,
            meeting_point="Tür",
            position=1,
            version=3,
        )
        self.first_todo = CanonicalTask.objects.create(
            station=self.station,
            text="Tische wischen",
            position=1,
        )
        self.client.force_login(self.user)

    def tearDown(self):
        reset_assignment_publisher()

    def post(self, name, payload, *, args=(), client=None, **extra):
        return (client or self.client).post(
            reverse(name, args=args),
            data=json.dumps(payload),
            content_type="application/json",
            **extra,
        )

    def test_check_and_reopen_are_idempotent_audited_and_keep_activity_durable(self):
        published = []
        configure_assignment_publisher(published.append)
        checked = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "todo-check-1", "expected_version": 1},
            args=(self.event.id, self.station.id, self.first_todo.id),
        )
        replay = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "todo-check-1", "expected_version": 1},
            args=(self.event.id, self.station.id, self.first_todo.id),
        )

        self.assertEqual(checked.status_code, 200)
        self.assertFalse(checked.json()["replayed"])
        self.assertTrue(replay.json()["replayed"])
        self.assertTrue(checked.json()["todo"]["checked"])
        self.assertEqual(checked.json()["todo"]["version"], 2)
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["kind"], "todo")
        self.assertEqual(
            AuditEvent.objects.filter(
                action="happy_cleaning.todo.check",
                request_id="todo-check-1",
            ).count(),
            1,
        )
        self.assertEqual(
            HappyCleaningCommandRequest.objects.filter(
                request_id="todo-check-1",
            ).count(),
            1,
        )
        progress = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "happy-cleaning-overview-station"},
            ),
            {"event_id": self.event.id, "station_id": self.station.id},
        ).json()["station"]
        self.assertEqual(
            (
                progress["todo_checked_count"],
                progress["todo_total_count"],
                progress["todo_progress_percentage"],
            ),
            (1, 1, 100),
        )

        reopened = self.post(
            "happy-cleaning-todo-reopen-api",
            {"request_id": "todo-reopen-1", "expected_version": 2},
            args=(self.event.id, self.station.id, self.first_todo.id),
        )

        self.assertEqual(reopened.status_code, 200)
        self.assertFalse(reopened.json()["todo"]["checked"])
        self.assertEqual(reopened.json()["todo"]["version"], 3)
        self.event.refresh_from_db()
        self.assertTrue(self.event.has_operational_activity)
        self.assertEqual(len(published), 2)
        progress = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "happy-cleaning-overview-station"},
            ),
            {"event_id": self.event.id, "station_id": self.station.id},
        ).json()["station"]
        self.assertEqual(
            (
                progress["todo_checked_count"],
                progress["todo_total_count"],
                progress["todo_progress_percentage"],
            ),
            (0, 1, 0),
        )

    def test_different_items_keep_independent_optimistic_versions_and_document_state(self):
        second = CanonicalTask.objects.create(
            station=self.station,
            text="Boden kehren",
            position=2,
            version=5,
        )

        first_response = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "different-item-1", "expected_version": 1},
            args=(self.event.id, self.station.id, self.first_todo.id),
        )
        second_response = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "different-item-2", "expected_version": 5},
            args=(self.event.id, self.station.id, second.id),
        )

        self.assertEqual(
            (first_response.status_code, second_response.status_code),
            (200, 200),
        )
        self.station.refresh_from_db()
        self.assertEqual(project_tasks(self.station.content_document), [
            {
                "id": self.first_todo.id,
                "text": "Tische wischen",
                "checked": True,
                "version": 2,
            },
            {
                "id": second.id,
                "text": "Boden kehren",
                "checked": True,
                "version": 6,
            },
        ])

    def test_http_authentication_csrf_json_turnus_and_expected_versions(self):
        url_args = (self.event.id, self.station.id, self.first_todo.id)
        anonymous = Client().post(
            reverse("happy-cleaning-todo-check-api", args=url_args),
            data=json.dumps({
                "request_id": "anonymous-check",
                "expected_version": 1,
            }),
            content_type="application/json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        missing_csrf = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "csrf-check", "expected_version": 1},
            args=url_args,
            client=csrf_client,
        )
        self.assertEqual(missing_csrf.status_code, 403)

        stale = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "stale-check", "expected_version": 9},
            args=url_args,
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json(), {
            "ok": False,
            "code": "stale",
            "current_version": 1,
            "replayed": False,
        })
        self.assertEqual(
            AuditEvent.objects.get(request_id="stale-check").outcome,
            "stale",
        )
        stale_replay = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "stale-check", "expected_version": 9},
            args=url_args,
        )
        self.assertEqual(stale_replay.status_code, 200)
        self.assertTrue(stale_replay.json()["replayed"])
        self.assertEqual(
            AuditEvent.objects.filter(request_id="stale-check").count(),
            1,
        )

        other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        other_event = HappyCleaning.objects.create(
            turnus=other_turnus,
            display_number=1,
        )
        other_station = HappyCleaningStation.objects.create(
            happy_cleaning=other_event,
            name="Privat",
            max_kids=1,
            meeting_point="Privat",
            position=1,
        )
        other_todo = CanonicalTask.objects.create(
            station=other_station,
            text="Private Aufgabe",
            position=1,
        )
        hidden = self.post(
            "happy-cleaning-todo-check-api",
            {"request_id": "hidden-check", "expected_version": 1},
            args=(other_event.id, other_station.id, other_todo.id),
        )
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json()["code"], "not_found")
        self.assertNotIn("Private Aufgabe", hidden.content.decode())
        self.assertEqual(
            AuditEvent.objects.get(request_id="hidden-check").outcome,
            "forbidden",
        )

    def test_audit_failure_rolls_back_and_emits_no_invalidation(self):
        published = []
        configure_assignment_publisher(published.append)

        with patch(
            "budo_app.happy_cleaning_todo_commands.audit_success",
            side_effect=ValidationError("audit failed"),
        ), self.assertRaises(ValidationError):
            self.post(
                "happy-cleaning-todo-check-api",
                {"request_id": "check-rollback", "expected_version": 1},
                args=(self.event.id, self.station.id, self.first_todo.id),
            )

        self.first_todo.refresh_from_db()
        self.event.refresh_from_db()
        self.assertFalse(self.first_todo.checked)
        self.assertEqual(self.first_todo.version, 1)
        self.assertEqual(self.event.revision, 4)
        self.assertFalse(self.event.has_operational_activity)
        self.assertFalse(HappyCleaningCommandRequest.objects.filter(
            request_id="check-rollback",
        ).exists())
        self.assertEqual(published, [])
