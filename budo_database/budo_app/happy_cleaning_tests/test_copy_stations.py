from unittest.mock import patch
from datetime import date

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from budo_app.happy_cleaning_station_matching import (
    normalize_station_name,
    station_names_are_similar,
)
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    HappyCleaningTodo,
    Turnus,
)


class StationNameMatcherTests(SimpleTestCase):
    def test_normalizes_unicode_case_umlauts_punctuation_and_spacing(self):
        table = {
            "  KÜCHE--Nord!  ": "kueche nord",
            "Ku\u0308che / Nord": "kueche nord",
            "Kueche.Nord": "kueche nord",
            "WC (Kinder) [A+B?]": "wc kinder a b",
        }
        for raw, expected in table.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_station_name(raw), expected)

    def test_matches_equality_or_shorter_full_word_containment_only(self):
        positives = [
            ("Küche", "KUECHE"),
            ("Bad", "Bad Kinder"),
            ("WC-Damen", "Großes WC Damen"),
            ("A+B?", "Station A+B?"),
        ]
        negatives = [
            ("Bad", "Badezimmer"),
            ("WC", "Waschcenter"),
            ("Speisesaal", "Esszimmer"),
            ("Bad", "Bäder"),
        ]
        for left, right in positives:
            with self.subTest(left=left, right=right):
                self.assertTrue(station_names_are_similar(left, right))
        for left, right in negatives:
            with self.subTest(left=left, right=right):
                self.assertFalse(station_names_are_similar(left, right))


class BulkStationCopyApiTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.active = Turnus.objects.create(
            turnus_nr=1, turnus_beginn=date(2026, 7, 1)
        )
        self.historical = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2025, 7, 1)
        )
        self.user = User.objects.create_user("copy-editor")
        self.user.profil.turnus = self.active
        self.user.profil.save(update_fields=["turnus"])
        self.active_responsible = User.objects.create_user("active-responsible")
        self.active_responsible.profil.turnus = self.active
        self.active_responsible.profil.save(update_fields=["turnus"])
        self.old_responsible = User.objects.create_user("old-responsible")
        self.old_responsible.profil.turnus = self.historical
        self.old_responsible.profil.save(update_fields=["turnus"])
        self.source = HappyCleaning.objects.create(
            turnus=self.historical, display_number=1
        )
        self.target = HappyCleaning.objects.create(
            turnus=self.active, display_number=1
        )
        self.other_target = HappyCleaning.objects.create(
            turnus=self.active, display_number=2
        )
        self.source_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.source,
            name="Küche",
            max_kids=5,
            meeting_point="Hof",
            wishes="Fenster",
            responsible_profile=self.old_responsible.profil,
            position=1,
        )
        self.source_todo = HappyCleaningTodo.objects.create(
            station=self.source_station,
            text="Boden wischen",
            position=1,
            checked=True,
            version=8,
        )
        self.source_station.refresh_from_db()
        self.source_station.content_document["content"].insert(0, {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Erst lüften."}],
        })
        self.source_station.save(update_fields=["content_document"])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def post(self, target, payload):
        return self.client.post(
            reverse("happy-cleaning-station-copy-api", args=[target.id]),
            payload,
            format="json",
        )

    def test_conflict_free_copy_is_atomic_deep_and_idempotent(self):
        payload = {
            "request_id": "bulk-copy-ok",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
        }
        response = self.post(self.target, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "copied")
        copied = HappyCleaningStation.objects.get(happy_cleaning=self.target)
        self.assertEqual(
            (copied.name, copied.max_kids, copied.meeting_point, copied.wishes),
            ("Küche", 5, "Hof", "Fenster"),
        )
        self.assertIsNone(copied.responsible_profile)
        copied_todo = copied.todos.get()
        self.assertNotEqual(copied_todo.id, self.source_todo.id)
        self.assertEqual(
            (copied_todo.text, copied_todo.checked, copied_todo.version),
            ("Boden wischen", False, 1),
        )
        self.assertEqual(
            copied.content_document["content"][0],
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Erst lüften."}],
            },
        )
        task_attrs = copied.content_document["content"][1]["content"][0]["attrs"]
        self.assertEqual(
            task_attrs,
            {"id": copied_todo.id, "checked": False, "version": 1},
        )
        self.source_todo.refresh_from_db()
        self.assertTrue(self.source_todo.checked)

        replay = self.post(self.target, payload)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(self.target.stations.count(), 1)

    def test_conflict_preview_is_revision_bound_stable_and_writes_nothing(self):
        HappyCleaningStation.objects.create(
            happy_cleaning=self.target,
            name="Große Küche Nord",
            max_kids=2,
            meeting_point="Gang",
            position=1,
        )
        payload = {
            "request_id": "bulk-copy-preview",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
        }
        response = self.post(self.target, payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["result"], "conflicts")
        self.assertEqual(body["target_revision"], 1)
        self.assertEqual(body["conflicts"][0]["source_station_id"], self.source_station.id)
        self.assertEqual(self.target.stations.count(), 1)
        self.assertFalse(
            AuditEvent.objects.filter(
                action="happy_cleaning.station.copy", outcome="success"
            ).exists()
        )
        replay = self.post(self.target, payload)
        self.assertEqual(replay.json()["conflicts"], body["conflicts"])
        self.assertTrue(replay.json()["replayed"])

    def test_resolves_conflicts_with_append_and_preserves_target_task_state(self):
        target_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.target,
            name="Große Küche",
            max_kids=9,
            meeting_point="Ziel",
            wishes="Behalten",
            responsible_profile=self.active_responsible.profil,
            position=1,
        )
        target_todo = HappyCleaningTodo.objects.create(
            station=target_station,
            text="Bestehend",
            position=1,
            checked=True,
            version=4,
        )
        preview = self.post(self.target, {
            "request_id": "append-preview",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
        }).json()
        response = self.post(self.target, {
            "request_id": "append-commit",
            "expected_revision": preview["target_revision"],
            "source_event_id": self.source.id,
            "station_ids": preview["station_ids"],
            "resolutions": [{
                "source_station_id": self.source_station.id,
                "target_station_id": target_station.id,
                "action": "append",
            }],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result_counts"]["appended"], 1)
        target_station.refresh_from_db()
        target_todo.refresh_from_db()
        self.assertEqual(
            (target_station.max_kids, target_station.meeting_point,
             target_station.wishes, target_station.responsible_profile_id),
            (9, "Ziel", "Behalten", self.active_responsible.profil.id),
        )
        self.assertEqual((target_todo.checked, target_todo.version), (True, 4))
        appended = target_station.todos.exclude(pk=target_todo.id).get()
        self.assertEqual((appended.checked, appended.version), (False, 1))
        self.assertEqual(
            target_station.content_document["content"][-3]["content"][0]["text"],
            "Kopiert aus Küche Happy Cleaning 1 – 2. Turnus 2025:",
        )

    def test_overwrite_preserves_identity_position_and_rejects_ineligible_target(self):
        target_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.target,
            name="Küche groß",
            max_kids=2,
            meeting_point="Alt",
            position=7,
        )
        response = self.post(self.target, {
            "request_id": "overwrite",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
            "resolutions": [{
                "source_station_id": self.source_station.id,
                "target_station_id": target_station.id,
                "action": "overwrite",
            }],
        })
        self.assertEqual(response.status_code, 200)
        target_station.refresh_from_db()
        self.assertEqual((target_station.name, target_station.position), ("Küche", 7))
        self.assertIsNone(target_station.responsible_profile)
        self.assertEqual(
            (target_station.todos.get().checked, target_station.todos.get().version),
            (False, 1),
        )

        target_station.has_ever_had_assignment = True
        target_station.save(update_fields=["has_ever_had_assignment"])
        rejected = self.post(self.target, {
            "request_id": "overwrite-locked",
            "expected_revision": self.target.revision + 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
            "resolutions": [{
                "source_station_id": self.source_station.id,
                "target_station_id": target_station.id,
                "action": "overwrite",
            }],
        })
        self.assertEqual(rejected.status_code, 409)

    def test_requires_exactly_one_resolution_per_conflicting_source(self):
        target_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.target,
            name="Küche Nord",
            max_kids=2,
            meeting_point="Gang",
            position=1,
        )
        payload = {
            "request_id": "missing-resolution",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
            "resolutions": [],
        }
        response = self.post(self.target, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.target.stations.count(), 1)
        target_station.refresh_from_db()
        self.assertEqual(target_station.name, "Küche Nord")

    def test_mixed_batch_skips_conflict_and_copies_conflict_free_source_idempotently(self):
        HappyCleaningStation.objects.create(
            happy_cleaning=self.target,
            name="Küche Nord",
            max_kids=2,
            meeting_point="Gang",
            position=1,
        )
        other_source = HappyCleaningStation.objects.create(
            happy_cleaning=self.source,
            name="Speisesaal",
            max_kids=8,
            meeting_point="Tür",
            position=2,
        )
        payload = {
            "request_id": "mixed-resolution",
            "expected_revision": 1,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id, other_source.id],
            "resolutions": [{
                "source_station_id": self.source_station.id,
                "target_station_id": None,
                "action": "skip",
            }],
        }
        response = self.post(self.target, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result_counts"],
            {
                "copied": 1, "overwritten": 0, "appended": 0,
                "skipped": 1, "todos_created": 0,
            },
        )
        self.assertTrue(
            self.target.stations.filter(name="Speisesaal").exists()
        )
        replay = self.post(self.target, payload)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(
            self.target.stations.filter(name="Speisesaal").count(), 1,
        )

    def test_rejects_source_target_and_inactive_target_and_rolls_back_failures(self):
        self.assertEqual(
            self.post(self.source, {
                "request_id": "historical-target",
                "expected_revision": 1,
                "source_event_id": self.target.id,
                "station_ids": [self.target.id],
            }).status_code,
            404,
        )
        self.assertEqual(
            self.post(self.target, {
                "request_id": "same-source",
                "expected_revision": 1,
                "source_event_id": self.target.id,
                "station_ids": [self.source_station.id],
            }).status_code,
            400,
        )
        stale = self.post(self.target, {
            "request_id": "stale-copy",
            "expected_revision": 99,
            "source_event_id": self.source.id,
            "station_ids": [self.source_station.id],
        })
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.target.stations.count(), 0)

        with patch(
            "budo_app.happy_cleaning_commands.audit_success",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self.post(self.target, {
                    "request_id": "audit-failure",
                    "expected_revision": 1,
                    "source_event_id": self.source.id,
                    "station_ids": [self.source_station.id],
                })
        self.assertEqual(self.target.stations.count(), 0)
        self.assertFalse(
            HappyCleaningCommandRequest.objects.filter(
                request_id="audit-failure"
            ).exists()
        )
