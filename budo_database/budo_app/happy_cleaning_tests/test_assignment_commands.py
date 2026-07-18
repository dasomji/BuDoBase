import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import include, path, reverse

from budo_app.happy_cleaning_assignment_publisher import (
    configure_assignment_publisher,
    reset_assignment_publisher,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Turnus,
)


urlpatterns = [
    path("api/happy-cleaning/", include("budo_app.happy_cleaning_assignment_urls")),
]


@override_settings(ROOT_URLCONF=__name__)
class HappyCleaningAssignmentCommandTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(username="assignment-operator")
        self.user.profil.rufname = "Mira"
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("rufname", "turnus"))
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=4,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=2,
            meeting_point="Tür",
            position=1,
        )
        self.target = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=1,
            meeting_point="Tür",
            position=2,
        )
        self.other_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="Hidden",
            max_kids=1,
            meeting_point="Hidden",
            position=1,
        )
        self.child = Kinder.objects.create(
            kid_index="HC-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            happy_cleaning_number=9,
        )
        self.second_child = Kinder.objects.create(
            kid_index="HC-2",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
            happy_cleaning_number=12,
        )
        self.other_child = Kinder.objects.create(
            kid_index="OTHER-1",
            kid_vorname="Private",
            kid_nachname="Person",
            turnus=self.other_turnus,
            happy_cleaning_number=9,
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

    def test_number_write_is_versioned_turnus_unique_idempotent_and_audited(self):
        url_name = "happy-cleaning-child-number-api"
        payload = {
            "request_id": "number-1",
            "number": 7,
            "expected_version": 1,
        }

        changed = self.post(url_name, payload, args=(self.child.id,))
        replayed = self.post(url_name, payload, args=(self.child.id,))

        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["child"], {
            "id": self.child.id,
            "full_name": "Ada Lovelace",
            "number": 7,
            "number_version": 2,
        })
        self.assertFalse(changed.json()["replayed"])
        self.assertTrue(replayed.json()["replayed"])
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 7)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assertEqual(
            AuditEvent.objects.filter(
                action="happy_cleaning.child_number.change",
                request_id="number-1",
            ).count(),
            1,
        )
        self.assertEqual(
            HappyCleaningCommandRequest.objects.filter(request_id="number-1").count(),
            1,
        )

    def test_duplicate_number_returns_clipped_authoritative_neighborhood(self):
        Kinder.objects.create(
            kid_index="HC-3",
            kid_vorname="Linus",
            kid_nachname="Torvalds",
            turnus=self.turnus,
            happy_cleaning_number=2,
        )
        response = self.post(
            "happy-cleaning-child-number-api",
            {"request_id": "duplicate-1", "number": 2, "expected_version": 1},
            args=(self.child.id,),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "duplicate_number")
        neighborhood = response.json()["neighborhood"]
        self.assertEqual([item["number"] for item in neighborhood], [1, 2, 3, 4, 5])
        self.assertEqual(neighborhood[1]["child"]["display_name"], "Linus Torvalds")
        self.assertNotIn("Private Person", response.content.decode())
        self.child.refresh_from_db()
        self.assertEqual(self.child.happy_cleaning_number, 9)
        replay = self.post(
            "happy-cleaning-child-number-api",
            {"request_id": "duplicate-1", "number": 2, "expected_version": 1},
            args=(self.child.id,),
        )
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(
            AuditEvent.objects.filter(request_id="duplicate-1", outcome="duplicate_number").count(),
            1,
        )

    def test_stale_number_returns_current_child_and_clear_uses_expected_version(self):
        stale = self.post(
            "happy-cleaning-child-number-api",
            {"request_id": "stale-number", "number": 5, "expected_version": 8},
            args=(self.child.id,),
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "stale")
        self.assertEqual(stale.json()["child"]["number"], 9)
        self.assertEqual(stale.json()["current_version"], 1)

        cleared = self.post(
            "happy-cleaning-child-number-api",
            {"request_id": "clear-number", "number": None, "expected_version": 1},
            args=(self.child.id,),
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["child"]["number"])
        self.assertEqual(cleared.json()["child"]["number_version"], 2)

    def test_assign_move_and_remove_are_atomic_versioned_and_mark_activity(self):
        assigned = self.post(
            "happy-cleaning-assignment-assign-api",
            {"request_id": "assign-1", "child_id": self.child.id, "station_id": self.station.id},
            args=(self.event.id,),
        )
        self.assertEqual(assigned.status_code, 200)
        version = assigned.json()["assignment"]["version"]
        self.assertEqual(assigned.json()["assignment"]["station"]["id"], self.station.id)

        moved = self.post(
            "happy-cleaning-assignment-move-api",
            {"request_id": "move-1", "station_id": self.target.id, "expected_version": version},
            args=(self.event.id, self.child.id),
        )
        self.assertEqual(moved.status_code, 200)
        moved_version = moved.json()["assignment"]["version"]
        self.assertGreater(moved_version, version)
        assignment = HappyCleaningAssignment.objects.get(child=self.child, happy_cleaning=self.event)
        self.assertEqual(assignment.station_id, self.target.id)

        removed = self.post(
            "happy-cleaning-assignment-remove-api",
            {"request_id": "remove-1", "expected_version": moved_version},
            args=(self.event.id, self.child.id),
        )
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.json()["assignment"]["station"])
        self.assertFalse(HappyCleaningAssignment.objects.filter(pk=assignment.id).exists())
        self.station.refresh_from_db()
        self.target.refresh_from_db()
        self.event.refresh_from_db()
        self.assertTrue(self.station.has_ever_had_assignment)
        self.assertTrue(self.target.has_ever_had_assignment)
        self.assertTrue(self.event.has_operational_activity)

    def test_full_or_stale_move_preserves_the_old_assignment(self):
        old = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.child,
            version=6,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.target,
            child=self.second_child,
            version=7,
        )

        full = self.post(
            "happy-cleaning-assignment-move-api",
            {"request_id": "move-full", "station_id": self.target.id, "expected_version": 6},
            args=(self.event.id, self.child.id),
        )
        self.assertEqual(full.status_code, 409)
        self.assertEqual(full.json()["code"], "station_full")
        old.refresh_from_db()
        self.assertEqual(old.station_id, self.station.id)

        stale = self.post(
            "happy-cleaning-assignment-remove-api",
            {"request_id": "remove-stale", "expected_version": 5},
            args=(self.event.id, self.child.id),
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["assignment"]["version"], 6)
        self.assertTrue(HappyCleaningAssignment.objects.filter(pk=old.id).exists())

    def test_cross_turnus_combinations_are_hidden_and_audited_without_names(self):
        hidden_event = self.post(
            "happy-cleaning-assignment-assign-api",
            {
                "request_id": "hidden-assignment",
                "child_id": self.other_child.id,
                "station_id": self.other_station.id,
            },
            args=(self.other_event.id,),
        )
        hidden_station = self.post(
            "happy-cleaning-assignment-assign-api",
            {
                "request_id": "hidden-station",
                "child_id": self.child.id,
                "station_id": self.other_station.id,
            },
            args=(self.event.id,),
        )
        hidden_child = self.post(
            "happy-cleaning-assignment-assign-api",
            {
                "request_id": "hidden-child",
                "child_id": self.other_child.id,
                "station_id": self.station.id,
            },
            args=(self.event.id,),
        )
        for response in (hidden_event, hidden_station, hidden_child):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["code"], "not_found")
            self.assertNotIn("Private", response.content.decode())
        self.assertEqual(
            AuditEvent.objects.get(request_id="hidden-assignment").outcome,
            "forbidden",
        )

    def test_http_authentication_csrf_json_and_validation(self):
        anonymous = Client().post(
            reverse("happy-cleaning-assignment-assign-api", args=(self.event.id,)),
            data=json.dumps({"request_id": "anonymous"}),
            content_type="application/json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        missing_csrf = self.post(
            "happy-cleaning-assignment-assign-api",
            {"request_id": "csrf", "child_id": self.child.id, "station_id": self.station.id},
            args=(self.event.id,),
            client=csrf_client,
        )
        self.assertEqual(missing_csrf.status_code, 403)
        csrf_token = "a" * 32
        csrf_client.cookies["csrftoken"] = csrf_token
        accepted = self.post(
            "happy-cleaning-assignment-assign-api",
            {
                "request_id": "csrf-accepted",
                "child_id": self.child.id,
                "station_id": self.station.id,
            },
            args=(self.event.id,),
            client=csrf_client,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted.status_code, 200)
        invalid = self.post(
            "happy-cleaning-child-number-api",
            {"request_id": "invalid", "number": 0, "expected_version": 1},
            args=(self.child.id,),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["code"], "validation_error")

    def test_audit_failure_rolls_back_domain_and_publisher_runs_only_after_commit(self):
        published = []
        configure_assignment_publisher(published.append)
        payload = {
            "request_id": "assign-rollback",
            "child_id": self.child.id,
            "station_id": self.station.id,
        }
        with patch(
            "budo_app.happy_cleaning_assignment_commands.audit_success",
            side_effect=ValidationError("audit failed"),
        ), self.assertRaises(ValidationError):
            self.post(
                "happy-cleaning-assignment-assign-api",
                payload,
                args=(self.event.id,),
            )
        self.assertFalse(HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event,
            child=self.child,
        ).exists())
        self.assertEqual(published, [])

        response = self.post(
            "happy-cleaning-assignment-assign-api",
            {**payload, "request_id": "assign-commit"},
            args=(self.event.id,),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["kind"], "assignment")

    def test_assignment_command_has_a_bounded_query_shape(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.post(
                "happy-cleaning-assignment-assign-api",
                {
                    "request_id": "assign-query-budget",
                    "child_id": self.child.id,
                    "station_id": self.station.id,
                },
                args=(self.event.id,),
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 24)
