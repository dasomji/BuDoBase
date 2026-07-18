import json
from datetime import date

from django.contrib.auth.models import Permission, User
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from budo_app.audit import (
    AuditEventData,
    AuditTransactionError,
    record_audit_event,
    record_rejected_attempt,
)
from budo_app.models import AuditEvent, Turnus


class AuditServiceTests(TransactionTestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="auditor")
        self.event = AuditEventData(
            turnus=self.turnus,
            actor_id=self.user.id,
            actor_label="Audit Teamer",
            action="happy_cleaning.event.create",
            outcome="success",
            resource_type="happy_cleaning",
            resource_id="41",
            resource_label="Happy Cleaning 1",
            request_id="req-123",
            client_ip="2001:0db8::1",
            user_agent="Audit Browser/1.0",
            details={"happy_cleaning_number": 1},
        )

    def test_writer_persists_only_allow_listed_canonical_data(self):
        event = record_audit_event(self.event)

        self.assertEqual(event.client_ip, "2001:db8::1")
        self.assertEqual(event.details, {"happy_cleaning_number": 1})
        self.assertEqual(event.actor_label, "Audit Teamer")

        forbidden = ("unknown", "password", "contact", "money")
        for key in forbidden:
            with self.subTest(key=key), self.assertRaises(ValidationError):
                record_audit_event(
                    AuditEventData(
                        **{
                            **self.event.__dict__,
                            "request_id": f"req-{key}",
                            "details": {key: "must never be stored"},
                        }
                    )
                )
        self.assertNotIn("must never be stored", json.dumps(list(
            AuditEvent.objects.values_list("details", flat=True)
        )))
        with self.assertRaises(ValidationError):
            record_audit_event(AuditEventData(**{
                **self.event.__dict__,
                "action": "unknown.domain.action",
                "request_id": "req-unknown-action",
                "details": {},
            }))
        with self.assertRaises(ValidationError):
            record_audit_event(AuditEventData(**{
                **self.event.__dict__,
                "request_id": "req-oversized",
                "details": {"station_name": "x" * 501},
            }))

    def test_rows_are_immutable_but_turnus_retention_cascade_deletes_them(self):
        event = record_audit_event(self.event)

        event.actor_label = "Changed"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).update(actor_label="Changed")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).delete()

        model_admin = admin.site._registry[AuditEvent]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, event))
        self.assertFalse(model_admin.has_delete_permission(None, event))

        actor_label = "Audit Teamer"
        self.user.delete()
        event.refresh_from_db()
        self.assertIsNotNone(event.actor_id)
        self.assertEqual(event.actor_label, actor_label)

        self.turnus.delete()
        self.assertFalse(AuditEvent.objects.filter(pk=event.pk).exists())

    def test_success_event_rolls_back_with_its_domain_transaction(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_audit_event(self.event)
                raise RuntimeError("domain mutation failed")

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_rejected_attempt_requires_a_healthy_autocommit_transaction(self):
        with transaction.atomic():
            with self.assertRaises(AuditTransactionError):
                record_rejected_attempt(
                    AuditEventData(**{**self.event.__dict__, "outcome": "forbidden"})
                )

        event = record_rejected_attempt(
            AuditEventData(**{**self.event.__dict__, "outcome": "forbidden"})
        )
        self.assertEqual(event.outcome, "forbidden")


class AuditHttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(username="reader", password="secret")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        self.client.force_login(self.user)

        self.own = AuditEvent.objects._create_validated_event(
            turnus=self.turnus,
            actor_id=10,
            actor_label="Ada Reader",
            action="happy_cleaning.event.create",
            outcome="success",
            resource_type="happy_cleaning",
            resource_id="1",
            resource_label="Happy Cleaning 1",
            request_id="own-1",
            client_ip="192.0.2.10",
            user_agent="Browser A",
            details={"happy_cleaning_number": 1},
        )
        AuditEvent.objects._create_validated_event(
            turnus=self.other_turnus,
            actor_id=11,
            actor_label="Other Reader",
            action="happy_cleaning.event.create",
            outcome="success",
            resource_type="happy_cleaning",
            resource_id="2",
            resource_label="Other Happy Cleaning",
            request_id="other-1",
            client_ip="192.0.2.11",
            user_agent="Browser B",
            details={"happy_cleaning_number": 2},
        )

    def _route(self, query=""):
        url = reverse("route-data-api", kwargs={"contract_key": "audit-events"})
        return self.client.get(f"{url}{query}")

    def test_read_requires_permission_and_never_leaks_another_turnus(self):
        denied = self._route()
        self.assertEqual(denied.status_code, 200)
        self.assertEqual(denied.json(), {"authorized": False, "events": []})

        self.user.user_permissions.add(Permission.objects.get(codename="view_auditevent"))
        response = self._route("?actor=Ada&action=happy_cleaning.event.create&page=1&page_size=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authorized"])
        self.assertEqual([item["id"] for item in payload["events"]], [self.own.id])
        self.assertEqual(payload["pagination"], {
            "page": 1,
            "page_size": 1,
            "total": 1,
            "pages": 1,
            "has_previous": False,
            "has_next": False,
        })
        self.assertNotIn("Other Reader", response.content.decode())

    def test_ordinary_reader_can_only_filter_their_active_turnus(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_auditevent"))

        own_response = self._route(f"?turnus={self.turnus.id}")
        other_response = self._route(f"?turnus={self.other_turnus.id}")

        self.assertEqual([event["id"] for event in own_response.json()["events"]], [self.own.id])
        self.assertEqual(own_response.json()["filters"]["turnus"], str(self.turnus.id))
        self.assertEqual(own_response.json()["filter_options"]["turnuses"], [
            {"id": self.turnus.id, "label": "T2-2026"},
        ])
        self.assertEqual(other_response.json()["events"], [])
        self.assertIn(
            f"turnus={self.other_turnus.id}",
            other_response.json()["export_url"],
        )
        self.assertNotIn("Other Reader", other_response.content.decode())

    def test_superuser_can_select_a_turnus_and_defaults_only_to_their_active_turnus(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])

        default_response = self._route()
        selected_response = self._route(f"?turnus={self.other_turnus.id}")

        self.assertEqual([event["id"] for event in default_response.json()["events"]], [self.own.id])
        selected_payload = selected_response.json()
        self.assertEqual(
            [event["actor"]["label"] for event in selected_payload["events"]],
            ["Other Reader"],
        )
        self.assertEqual(selected_payload["filters"]["turnus"], str(self.other_turnus.id))
        self.assertEqual(selected_payload["filter_options"]["turnuses"], [
            {"id": self.turnus.id, "label": "T2-2026"},
            {"id": self.other_turnus.id, "label": "T3-2026"},
        ])

    def test_superuser_without_an_active_turnus_has_no_implicit_audit_scope(self):
        superuser = User.objects.create_superuser(
            username="unscoped-admin",
            password="secret",
        )
        self.client.force_login(superuser)

        read_response = self._route()
        export_response = self.client.get(reverse("audit-export-api"))

        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["events"], [])
        self.assertEqual(export_response.status_code, 404)

    def test_export_is_versioned_deterministic_and_logs_non_recursively(self):
        self.user.user_permissions.add(Permission.objects.get(codename="export_auditevent"))

        denied = self.client.get(reverse("audit-export-api"))
        self.assertEqual(denied.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_auditevent"))
        response = self.client.get(
            reverse("audit-export-api"),
            HTTP_X_REQUEST_ID="export-request",
            HTTP_USER_AGENT="Export Browser",
            REMOTE_ADDR="192.0.2.44",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="audit-T2-2026\.log"')
        exported_text = b"".join(response.streaming_content).decode()
        lines = [json.loads(line) for line in exported_text.splitlines()]
        self.assertEqual(lines[0], {
            "record_type": "header",
            "schema": "budo.audit",
            "version": 1,
            "turnus": {"id": self.turnus.id, "label": "T2-2026"},
        })
        self.assertEqual([line["id"] for line in lines[1:]], [self.own.id])
        export_event = AuditEvent.objects.get(action="audit.export")
        self.assertNotIn(export_event.id, [line.get("id") for line in lines])
        self.assertEqual(export_event.client_ip, "192.0.2.44")

        for sensitive in ("password", "token", "cookie", "health", "contact", "money"):
            self.assertNotIn(sensitive, exported_text.lower())

    def test_export_turnus_selection_matches_read_permissions(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_auditevent"),
            Permission.objects.get(codename="export_auditevent"),
        )

        forbidden = self.client.get(
            f'{reverse("audit-export-api")}?turnus={self.other_turnus.id}'
        )
        self.assertEqual(forbidden.status_code, 404)

        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        response = self.client.get(
            f'{reverse("audit-export-api")}?turnus={self.other_turnus.id}',
            HTTP_X_REQUEST_ID="other-turnus-export",
        )

        self.assertEqual(response.status_code, 200)
        lines = [
            json.loads(line)
            for line in b"".join(response.streaming_content).decode().splitlines()
        ]
        self.assertEqual(lines[0]["turnus"], {
            "id": self.other_turnus.id,
            "label": "T3-2026",
        })
        self.assertEqual([line["actor"]["label"] for line in lines[1:]], ["Other Reader"])
        export_event = AuditEvent.objects.get(request_id="other-turnus-export")
        self.assertEqual(export_event.turnus, self.other_turnus)
        self.assertNotIn(export_event.id, [line.get("id") for line in lines])
