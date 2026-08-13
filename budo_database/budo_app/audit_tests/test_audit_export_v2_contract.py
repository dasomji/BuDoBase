"""RED contract for sensitive full-payload audit export v2 (#164-07)."""

import json
import tempfile
from dataclasses import replace
from datetime import date
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from budo_app import audit_exports
from budo_app.audit import AuditEventData, record_audit_event
from budo_app.audit_queries import FILTER_NAMES, serialize_audit_event
from budo_app.audit_tests.test_kid_edit_audit_schema import valid_details
from budo_app.memberships import create_membership, select_turnus
from budo_app.models import AuditEvent, Turnus, TurnusMembership


PRIVACY_HEADERS = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class AuditExportV2HttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create(username="export-reader", is_staff=True)
        self.view_permission = Permission.objects.get(codename="view_auditevent")
        self.export_permission = Permission.objects.get(
            codename="export_auditevent",
        )
        self.user.user_permissions.add(
            self.view_permission, self.export_permission,
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.url = reverse("audit-export-api")

    def event(self, *, turnus=None, action="happy_cleaning.event.create",
              details=None, request_id="source"):
        return AuditEvent.objects._create_validated_event(
            turnus=turnus or self.turnus, actor_id=self.user.id,
            actor_label="Export Reader", action=action, outcome="success",
            resource_type="child" if action == "kid.edit" else "happy_cleaning",
            resource_id="27", resource_label="Export source",
            request_id=request_id, client_ip="192.0.2.10",
            user_agent="Source Browser",
            details={} if details is None else details,
        )

    def lines(self, response):
        return [
            json.loads(line)
            for line in b"".join(response.streaming_content).decode().splitlines()
        ]

    def assert_privacy_headers(self, response, *, attachment=False):
        for name, value in PRIVACY_HEADERS.items():
            self.assertEqual(response.headers.get(name), value, name)
        self.assertIn(
            "Cookie",
            {item.strip() for item in response.headers.get("Vary", "").split(",")},
        )
        if attachment:
            self.assertRegex(
                response.headers.get("Content-Disposition", ""),
                r'^attachment; filename="audit-T2-2026\.log"$',
            )
            self.assertEqual(
                response.headers.get("Content-Type"),
                "application/x-ndjson; charset=utf-8",
            )

    def test_v2_snapshot_streams_full_events_and_excludes_later_rows(self):
        details = valid_details()
        source = self.event(action="kid.edit", details=details, request_id="kid")
        with mock.patch.object(
            tempfile, "NamedTemporaryFile",
        ) as named, mock.patch.object(
            tempfile, "TemporaryFile",
        ) as temporary, mock.patch.object(tempfile, "mkstemp") as mkstemp:
            response = self.client.get(
                self.url, HTTP_X_REQUEST_ID="export-v2",
                HTTP_USER_AGENT="Export Browser", REMOTE_ADDR="192.0.2.44",
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)
            issuance = AuditEvent.objects.get(request_id="export-v2")
            self.assertEqual(issuance.action, "audit.export")
            self.assertEqual(issuance.resource_type, "audit_log")
            self.assertEqual(issuance.resource_id, str(self.turnus.id))
            self.assertEqual(issuance.details, {
                "result_count": 1, "filter_count": 0,
            })
            appended = self.event(request_id="after-issuance")
            with CaptureQueriesContext(connection) as consumption_queries:
                lines = self.lines(response)
            self.assertEqual(
                consumption_queries.captured_queries,
                [],
                "protected export rows must be materialized before the "
                "membership-lock transaction ends",
            )
        named.assert_not_called()
        temporary.assert_not_called()
        mkstemp.assert_not_called()

        self.assertEqual(lines[0], {
            "record_type": "header",
            "schema": "budo.audit",
            "version": 2,
            "classification": "sensitive-personal-data",
            "payload_policy": "full-authorized",
            "turnus": {"id": self.turnus.id, "label": str(self.turnus)},
            "snapshot_id": source.id,
        })
        self.assertEqual(lines[1:], [serialize_audit_event(source)])
        self.assertEqual(lines[1]["details"], details)
        self.assertNotIn(issuance.id, [line.get("id") for line in lines])
        self.assertNotIn(appended.id, [line.get("id") for line in lines])
        self.assert_privacy_headers(response, attachment=True)

    def test_empty_turnus_uses_zero_snapshot_and_excludes_its_issuance(self):
        TurnusMembership.objects.create(user=self.user, turnus=self.other_turnus)
        self.user.profil.selected_turnus = self.other_turnus
        self.user.profil.save(update_fields=["selected_turnus"])
        response = self.client.get(self.url, HTTP_X_REQUEST_ID="empty-export")

        self.assertEqual(response.status_code, 200)
        lines = self.lines(response)
        self.assertEqual(lines, [{
            "record_type": "header", "schema": "budo.audit", "version": 2,
            "classification": "sensitive-personal-data",
            "payload_policy": "full-authorized",
            "turnus": {"id": self.other_turnus.id,
                       "label": str(self.other_turnus)},
            "snapshot_id": 0,
        }])
        issuance = AuditEvent.objects.get(request_id="empty-export")
        self.assertEqual(issuance.details["result_count"], 0)

    def test_large_snapshot_rolls_to_disk_and_survives_membership_removal(self):
        membership = TurnusMembership.objects.get(
            user=self.user, turnus=self.turnus,
        )
        self.event(details={"station_name": "x" * 256})
        snapshot = tempfile.SpooledTemporaryFile(max_size=8, mode="w+b")

        with mock.patch.object(
            audit_exports, "create_export_snapshot", return_value=snapshot,
        ):
            response = self.client.get(self.url)

        self.assertTrue(snapshot._rolled)
        membership.delete()
        lines = self.lines(response)
        self.assertEqual(lines[1]["details"]["station_name"], "x" * 256)
        self.assertTrue(snapshot.closed)

    def test_abandoned_snapshot_closes_with_response(self):
        self.event(details={"station_name": "x" * 256})
        snapshot = tempfile.SpooledTemporaryFile(max_size=8, mode="w+b")

        with mock.patch.object(
            audit_exports, "create_export_snapshot", return_value=snapshot,
        ):
            response = self.client.get(self.url)

        self.assertFalse(snapshot.closed)
        with mock.patch("django.http.response.signals.request_finished.send"):
            response.close()
        self.assertTrue(snapshot.closed)

    def test_insertion_exceptions_return_sanitized_503_without_a_stream(self):
        self.event(details={"station_name": "MUST-NOT-LEAK"})
        self.client.raise_request_exception = False
        for error in (
            ValidationError("insert failed"), DatabaseError("insert failed"),
            RuntimeError("SECRET-INSERT-FAILURE"),
        ):
            with self.subTest(error=type(error).__name__), mock.patch.object(
                audit_exports, "record_audit_event", side_effect=error,
            ):
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 503)
                self.assertFalse(response.streaming)
                rendered = response.content.decode()
                self.assertNotIn("MUST-NOT-LEAK", rendered)
                self.assertNotIn("SECRET-INSERT-FAILURE", rendered)
                self.assert_privacy_headers(response)

    def test_privacy_headers_cover_forbidden_and_unavailable_scope(self):
        self.user.user_permissions.remove(self.export_permission)
        forbidden = self.client.get(self.url)
        self.user.user_permissions.add(self.export_permission)
        unavailable = self.client.get(
            self.url, {"turnus": self.other_turnus.id},
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(unavailable.status_code, 404)
        self.assert_privacy_headers(forbidden)
        self.assert_privacy_headers(unavailable)


class AuditExportSchemaTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.data = AuditEventData(
            turnus=self.turnus, actor_id=7, actor_label="Export Reader",
            action="audit.export", outcome="success", resource_type="audit_log",
            resource_id=str(self.turnus.id), resource_label=f"Audit log {self.turnus}",
            request_id="export-schema", client_ip=None, user_agent="tests",
            details={"result_count": 0, "filter_count": 0},
        )

    def test_snapshot_closes_when_stream_iterator_is_abandoned(self):
        snapshot = tempfile.SpooledTemporaryFile(max_size=8, mode="w+b")
        snapshot.write(b"partial")
        snapshot.seek(0)
        stream = audit_exports.stream_snapshot(snapshot)

        self.assertEqual(next(stream), b"partial")
        stream.close()

        self.assertTrue(snapshot.closed)

    def test_schema_envelope_and_ranges_are_exact(self):
        try:
            created = record_audit_event(self.data)
        except ValidationError as error:
            self.fail(f"valid audit.export metadata was rejected: {error}")
        self.assertEqual(created.details, self.data.details)
        record_audit_event(replace(
            self.data, request_id="export-upper",
            details={
                "result_count": 9_223_372_036_854_775_807,
                "filter_count": len(FILTER_NAMES),
            },
        ))

        invalid = (
            {"result_count": 0},
            {**self.data.details, "extra": 1},
            {"result_count": True, "filter_count": 0},
            {"result_count": -1, "filter_count": 0},
            {"result_count": 0, "filter_count": len(FILTER_NAMES) + 1},
            {"result_count": 9_223_372_036_854_775_808, "filter_count": 0},
        )
        accepted = []
        for index, details in enumerate(invalid):
            try:
                record_audit_event(replace(
                    self.data, request_id=f"invalid-export-{index}",
                    details=details,
                ))
            except ValidationError:
                continue
            accepted.append(index)
        self.assertEqual(accepted, [])

        for outcome, resource_type, resource_id in (
            ("forbidden", "audit_log", str(self.turnus.id)),
            ("success", "audit_event", str(self.turnus.id)),
            ("success", "audit_log", str(self.turnus.id + 1)),
        ):
            with self.subTest(outcome=outcome, resource_type=resource_type), \
                    self.assertRaises(ValidationError):
                record_audit_event(replace(
                    self.data, request_id=f"bad-export-{outcome}-{resource_type}",
                    outcome=outcome, resource_type=resource_type,
                    resource_id=resource_id,
                ))
