import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TransactionTestCase
from django.urls import reverse

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
    HappyCleaningTodo,
    Kinder,
    Turnus,
)


class HappyCleaningEventCommandTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 6, 1),
        )
        self.user = User.objects.create_user(
            username="happy-cleaning-editor",
            password="secret",
        )
        self.user.profil.rufname = "Mira"
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["rufname", "turnus"])
        self.client.force_login(self.user)

    def post_json(self, url, payload, **extra):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            **extra,
        )

    def test_create_allocates_the_next_number_and_replays_one_atomic_audit(self):
        HappyCleaning.objects.create(turnus=self.turnus, display_number=1)
        HappyCleaning.objects.create(turnus=self.other_turnus, display_number=8)
        url = reverse("happy-cleaning-event-create-api")
        payload = {"request_id": "event-create-1"}

        created = self.post_json(
            url,
            payload,
            REMOTE_ADDR="192.0.2.9",
            HTTP_USER_AGENT="Command Browser",
        )
        replayed = self.post_json(url, payload)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["event"]["display_number"], 2)
        self.assertFalse(created.json()["replayed"])
        self.assertEqual(replayed.status_code, 200)
        self.assertEqual(replayed.json()["event"], created.json()["event"])
        self.assertTrue(replayed.json()["replayed"])
        self.assertEqual(
            list(HappyCleaning.objects.filter(turnus=self.turnus).values_list(
                "display_number", flat=True,
            )),
            [1, 2],
        )
        audit = AuditEvent.objects.get(action="happy_cleaning.event.create")
        self.assertEqual(audit.request_id, "event-create-1")
        self.assertEqual(audit.details, {"happy_cleaning_number": 2})
        self.assertEqual(audit.client_ip, "192.0.2.9")

    def test_create_requires_authentication_csrf_json_and_a_request_id(self):
        url = reverse("happy-cleaning-event-create-api")
        anonymous = Client().post(
            url,
            data=json.dumps({"request_id": "anonymous"}),
            content_type="application/json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        without_csrf = csrf_client.post(
            url,
            data=json.dumps({"request_id": "missing-csrf"}),
            content_type="application/json",
        )
        self.assertEqual(without_csrf.status_code, 403)
        token = csrf_client.get(reverse("bootstrap-api")).json()["csrf_token"]
        accepted = csrf_client.post(
            url,
            data=json.dumps({"request_id": "with-csrf"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 201)

        missing = self.post_json(url, {})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["errors"], {
            "request_id": ["This field is required."],
        })

    def test_create_rolls_back_domain_and_idempotency_when_audit_fails(self):
        with patch(
            "budo_app.happy_cleaning_commands.record_audit_event",
            side_effect=RuntimeError("audit unavailable"),
        ), self.assertRaises(RuntimeError):
            self.post_json(
                reverse("happy-cleaning-event-create-api"),
                {"request_id": "event-create-audit-failure"},
            )

        self.assertEqual(HappyCleaning.objects.count(), 0)
        self.assertEqual(HappyCleaningCommandRequest.objects.count(), 0)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_delete_renumbers_transactionally_and_permanent_activity_locks_it(self):
        first = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=2,
        )
        locked = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=4,
            has_operational_activity=True,
        )
        third = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=3,
            revision=7,
        )

        deleted = self.post_json(
            reverse("happy-cleaning-event-delete-api", args=[first.id]),
            {"request_id": "event-delete-1", "expected_revision": 2},
        )
        self.assertEqual(deleted.status_code, 200)
        locked.refresh_from_db()
        third.refresh_from_db()
        self.assertEqual((locked.display_number, locked.revision), (1, 5))
        self.assertEqual((third.display_number, third.revision), (2, 8))

        denied = self.post_json(
            reverse("happy-cleaning-event-delete-api", args=[locked.id]),
            {"request_id": "event-delete-locked", "expected_revision": 5},
        )
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(denied.json()["code"], "event_locked")
        self.assertTrue(HappyCleaning.objects.filter(pk=locked.id).exists())

    def test_stale_and_cross_turnus_delete_are_rejected_and_audited_without_leak(self):
        event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=3,
        )
        other = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=3,
        )

        stale = self.post_json(
            reverse("happy-cleaning-event-delete-api", args=[event.id]),
            {"request_id": "event-delete-stale", "expected_revision": 2},
        )
        hidden = self.post_json(
            reverse("happy-cleaning-event-delete-api", args=[other.id]),
            {"request_id": "event-delete-hidden", "expected_revision": 3},
        )

        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json(), {
            "ok": False,
            "code": "stale",
            "current_version": 3,
        })
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json(), {"ok": False, "code": "not_found"})
        self.assertCountEqual(
            AuditEvent.objects.values_list("outcome", flat=True),
            ["stale", "forbidden"],
        )


class HappyCleaningStationCommandTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 6, 1),
        )
        self.user = User.objects.create_user(username="station-editor")
        self.user.profil.rufname = "Mira"
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["rufname", "turnus"])
        self.other_user = User.objects.create_user(username="other-editor")
        self.other_user.profil.rufname = "Other"
        self.other_user.profil.turnus = self.other_turnus
        self.other_user.profil.save(update_fields=["rufname", "turnus"])
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=1,
        )
        self.client.force_login(self.user)

    def post_json(self, name, args, payload):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def station_payload(self, request_id, **overrides):
        return {
            "request_id": request_id,
            "expected_revision": self.event.revision,
            "name": "Speisesaal",
            "max_kids": 4,
            "meeting_point": "Vor dem Speisesaal",
            "wishes": "Fenster",
            "responsible_profile_id": self.user.profil.id,
            **overrides,
        }

    def test_create_and_update_validate_fields_responsible_and_versions(self):
        created = self.post_json(
            "happy-cleaning-station-create-api",
            [self.event.id],
            self.station_payload("station-create-1"),
        )
        self.assertEqual(created.status_code, 201)
        station_id = created.json()["station"]["id"]
        station = HappyCleaningStation.objects.get(pk=station_id)
        self.assertEqual(station.position, 1)
        self.assertEqual(station.responsible_profile, self.user.profil)
        self.event.refresh_from_db()
        self.assertEqual(self.event.revision, 2)

        updated = self.post_json(
            "happy-cleaning-station-update-api",
            [self.event.id, station.id],
            {
                "request_id": "station-update-1",
                "expected_version": 1,
                "name": "Großer Speisesaal",
                "max_kids": 5,
                "meeting_point": "Haupteingang",
                "wishes": "",
                "responsible_profile_id": None,
            },
        )
        self.assertEqual(updated.status_code, 200)
        station.refresh_from_db()
        self.assertEqual((station.name, station.max_kids, station.version), (
            "Großer Speisesaal", 5, 2,
        ))

        invalid = self.post_json(
            "happy-cleaning-station-create-api",
            [self.event.id],
            self.station_payload(
                "station-create-invalid",
                expected_revision=3,
                name=" ",
                max_kids=0,
                meeting_point="",
            ),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(set(invalid.json()["errors"]), {
            "name", "max_kids", "meeting_point",
        })

        hidden_profile = self.post_json(
            "happy-cleaning-station-update-api",
            [self.event.id, station.id],
            {
                "request_id": "station-update-other-profile",
                "expected_version": 2,
                "name": station.name,
                "max_kids": station.max_kids,
                "meeting_point": station.meeting_point,
                "wishes": "",
                "responsible_profile_id": self.other_user.profil.id,
            },
        )
        self.assertEqual(hidden_profile.status_code, 404)
        self.assertEqual(hidden_profile.json()["code"], "not_found")
        self.assertTrue(AuditEvent.objects.filter(
            action="happy_cleaning.station.update",
            outcome="forbidden",
        ).exists())

    def test_station_master_data_writes_emit_no_todo_invalidation(self):
        published = []
        configure_assignment_publisher(published.append)
        try:
            created = self.post_json(
                "happy-cleaning-station-create-api",
                [self.event.id],
                self.station_payload("station-create-without-invalidation"),
            )
            self.assertEqual(created.status_code, 201)
            station = HappyCleaningStation.objects.get(
                pk=created.json()["station"]["id"],
            )

            updated = self.post_json(
                "happy-cleaning-station-update-api",
                [self.event.id, station.id],
                {
                    "request_id": "station-update-without-invalidation",
                    "expected_version": station.version,
                    "name": "Großer Speisesaal",
                    "max_kids": station.max_kids,
                    "meeting_point": station.meeting_point,
                    "wishes": station.wishes,
                    "responsible_profile_id": station.responsible_profile_id,
                },
            )
            self.assertEqual(updated.status_code, 200)

            self.event.refresh_from_db()
            second = self.post_json(
                "happy-cleaning-station-create-api",
                [self.event.id],
                self.station_payload(
                    "station-create-second-without-invalidation",
                    expected_revision=self.event.revision,
                    name="Bad",
                ),
            )
            self.assertEqual(second.status_code, 201)
            second_id = second.json()["station"]["id"]

            self.event.refresh_from_db()
            reordered = self.post_json(
                "happy-cleaning-station-reorder-api",
                [self.event.id],
                {
                    "request_id": "station-reorder-without-invalidation",
                    "expected_revision": self.event.revision,
                    "station_ids": [second_id, station.id],
                },
            )
            self.assertEqual(reordered.status_code, 200)

            station.refresh_from_db()
            deleted = self.post_json(
                "happy-cleaning-station-delete-api",
                [self.event.id, station.id],
                {
                    "request_id": "station-delete-without-invalidation",
                    "expected_version": station.version,
                },
            )
            self.assertEqual(deleted.status_code, 200)

            source = HappyCleaning.objects.create(
                turnus=self.other_turnus,
                display_number=1,
            )
            HappyCleaningStation.objects.create(
                happy_cleaning=source,
                name="Quelle",
                max_kids=2,
                meeting_point="Quelltreffpunkt",
                position=1,
            )
            self.event.refresh_from_db()
            copied = self.post_json(
                "happy-cleaning-station-copy-api",
                [self.event.id],
                {
                    "request_id": "station-copy-without-invalidation",
                    "expected_revision": self.event.revision,
                    "source_event_id": source.id,
                    "copy_all": True,
                },
            )
            self.assertEqual(copied.status_code, 200)
            self.assertEqual(published, [])
        finally:
            reset_assignment_publisher()

    def test_capacity_and_delete_lock_survive_assignment_removal(self):
        station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Tür",
            position=1,
        )
        child = Kinder.objects.create(
            kid_index="HC-LOCK",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
        )
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=station,
            child=child,
        )
        assignment.delete()
        station.refresh_from_db()
        self.assertTrue(station.has_ever_had_assignment)

        capacity = self.post_json(
            "happy-cleaning-station-update-api",
            [self.event.id, station.id],
            {
                "request_id": "station-capacity-locked",
                "expected_version": 1,
                "name": "Küche neu",
                "max_kids": 3,
                "meeting_point": "Tür",
                "wishes": "",
                "responsible_profile_id": None,
            },
        )
        self.assertEqual(capacity.status_code, 409)
        self.assertEqual(capacity.json()["code"], "capacity_locked")

        deleted = self.post_json(
            "happy-cleaning-station-delete-api",
            [self.event.id, station.id],
            {"request_id": "station-delete-locked", "expected_version": 1},
        )
        self.assertEqual(deleted.status_code, 409)
        self.assertEqual(deleted.json()["code"], "station_locked")

    def test_station_reorder_is_gap_free_and_rejects_stale_or_incomplete_ids(self):
        stations = [
            HappyCleaningStation.objects.create(
                happy_cleaning=self.event,
                name=name,
                max_kids=2,
                meeting_point="Treffpunkt",
                position=position,
            )
            for position, name in enumerate(("A", "B", "C"), start=1)
        ]
        reordered = self.post_json(
            "happy-cleaning-station-reorder-api",
            [self.event.id],
            {
                "request_id": "station-reorder-1",
                "expected_revision": 1,
                "station_ids": [stations[2].id, stations[0].id, stations[1].id],
            },
        )
        self.assertEqual(reordered.status_code, 200)
        self.assertEqual(
            list(HappyCleaningStation.objects.filter(
                happy_cleaning=self.event,
            ).values_list("id", "position")),
            [(stations[2].id, 1), (stations[0].id, 2), (stations[1].id, 3)],
        )

        incomplete = self.post_json(
            "happy-cleaning-station-reorder-api",
            [self.event.id],
            {
                "request_id": "station-reorder-incomplete",
                "expected_revision": 2,
                "station_ids": [stations[0].id],
            },
        )
        self.assertEqual(incomplete.status_code, 400)
        self.assertEqual(incomplete.json()["code"], "invalid_order")

        stale = self.post_json(
            "happy-cleaning-station-reorder-api",
            [self.event.id],
            {
                "request_id": "station-reorder-stale",
                "expected_revision": 1,
                "station_ids": [station.id for station in stations],
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertTrue(AuditEvent.objects.filter(
            action="happy_cleaning.station.reorder",
            outcome="stale",
        ).exists())

    def test_todo_create_update_reorder_and_delete_preserve_checked_state(self):
        station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Tür",
            position=1,
        )
        first = self.post_json(
            "happy-cleaning-todo-create-api",
            [self.event.id, station.id],
            {
                "request_id": "todo-create-1",
                "expected_version": 1,
                "text": "Boden kehren",
            },
        )
        self.assertEqual(first.status_code, 201)
        second = self.post_json(
            "happy-cleaning-todo-create-api",
            [self.event.id, station.id],
            {
                "request_id": "todo-create-2",
                "expected_version": 2,
                "text": "Tische wischen",
            },
        )
        first_id = first.json()["todo"]["id"]
        second_id = second.json()["todo"]["id"]
        HappyCleaningTodo.objects.filter(pk=first_id).update(checked=True)

        updated = self.post_json(
            "happy-cleaning-todo-update-api",
            [self.event.id, station.id, first_id],
            {
                "request_id": "todo-update-1",
                "expected_version": 1,
                "text": "Boden gründlich kehren",
            },
        )
        self.assertEqual(updated.status_code, 200)
        todo = HappyCleaningTodo.objects.get(pk=first_id)
        self.assertTrue(todo.checked)
        self.assertEqual(todo.text, "Boden gründlich kehren")

        station.refresh_from_db()
        reordered = self.post_json(
            "happy-cleaning-todo-reorder-api",
            [self.event.id, station.id],
            {
                "request_id": "todo-reorder-1",
                "expected_version": station.version,
                "todo_ids": [second_id, first_id],
            },
        )
        self.assertEqual(reordered.status_code, 200)
        self.assertEqual(
            list(HappyCleaningTodo.objects.filter(station=station).values_list(
                "id", "position", "checked",
            )),
            [(second_id, 1, False), (first_id, 2, True)],
        )

        second_version = HappyCleaningTodo.objects.get(pk=second_id).version
        deleted = self.post_json(
            "happy-cleaning-todo-delete-api",
            [self.event.id, station.id, second_id],
            {
                "request_id": "todo-delete-1",
                "expected_version": second_version,
            },
        )
        self.assertEqual(deleted.status_code, 200)
        remaining = HappyCleaningTodo.objects.get(pk=first_id)
        self.assertEqual(remaining.position, 1)

    def test_copy_deep_copies_selected_or_all_with_explicit_duplicate_policy(self):
        source_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=1,
        )
        source_a = HappyCleaningStation.objects.create(
            happy_cleaning=source_event,
            name="Küche",
            max_kids=3,
            meeting_point="Quelle A",
            wishes="Wunsch",
            responsible_profile=self.other_user.profil,
            position=1,
        )
        source_b = HappyCleaningStation.objects.create(
            happy_cleaning=source_event,
            name="Bad",
            max_kids=2,
            meeting_point="Quelle B",
            position=2,
        )
        source_todo = HappyCleaningTodo.objects.create(
            station=source_a,
            text="Alles putzen",
            position=1,
            checked=True,
            version=5,
        )
        existing = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=1,
            meeting_point="Ziel",
            position=1,
        )
        child = Kinder.objects.create(
            kid_index="COPY-KID",
            turnus=self.other_turnus,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=source_event,
            station=source_a,
            child=child,
        )
        url_args = [self.event.id]
        base = {
            "request_id": "copy-1",
            "expected_revision": 1,
            "source_event_id": source_event.id,
            "copy_all": True,
        }

        warning = self.post_json(
            "happy-cleaning-station-copy-api",
            url_args,
            base,
        )
        self.assertEqual(warning.status_code, 409)
        self.assertEqual(warning.json(), {
            "ok": False,
            "code": "duplicate_names",
            "duplicate_names": ["Küche"],
        })

        copied = self.post_json(
            "happy-cleaning-station-copy-api",
            url_args,
            {**base, "duplicate_strategy": "copy"},
        )
        self.assertEqual(copied.status_code, 200)
        target = list(HappyCleaningStation.objects.filter(
            happy_cleaning=self.event,
        ).prefetch_related("todos"))
        self.assertEqual([item.name for item in target], ["Küche", "Küche", "Bad"])
        copied_a = target[1]
        self.assertIsNone(copied_a.responsible_profile)
        self.assertEqual(copied_a.position, 2)
        self.assertEqual(copied_a.assignments.count(), 0)
        copied_todo = copied_a.todos.get()
        self.assertNotEqual(copied_todo.id, source_todo.id)
        self.assertEqual((copied_todo.text, copied_todo.checked, copied_todo.version), (
            "Alles putzen", False, 1,
        ))
        existing.refresh_from_db()
        self.assertEqual(existing.position, 1)

        same_turnus_target = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
        )
        retained = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Wiese",
            max_kids=2,
            meeting_point="Baum",
            responsible_profile=self.user.profil,
            position=4,
        )
        selected = self.post_json(
            "happy-cleaning-station-copy-api",
            [same_turnus_target.id],
            {
                "request_id": "copy-selected",
                "expected_revision": same_turnus_target.revision,
                "source_event_id": self.event.id,
                "station_ids": [retained.id],
            },
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(
            HappyCleaningStation.objects.get(
                happy_cleaning=same_turnus_target,
                name="Wiese",
            ).responsible_profile,
            self.user.profil,
        )
