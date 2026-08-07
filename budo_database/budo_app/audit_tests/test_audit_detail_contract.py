"""RED contract for one-event audit detail reads (#164-06)."""

from dataclasses import replace
from datetime import date
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, resolve

from budo_app import audit_views
from budo_app.audit import AuditEventData, record_audit_event
from budo_app.audit_queries import serialize_audit_event
from budo_app.audit_tests.test_kid_edit_audit_schema import valid_details
from budo_app.models import AuditEvent, Turnus


PRIVACY_HEADERS = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class AuditDetailHttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create(username="detail-reader", is_staff=True)
        self.permission = Permission.objects.get(codename="view_auditevent")
        self.user.user_permissions.add(self.permission)
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        self.client.force_login(self.user)

    def event(self, *, turnus=None, action="happy_cleaning.event.create",
              details=None, request_id="source", resource_type=None,
              resource_label="Source event"):
        return AuditEvent.objects._create_validated_event(
            turnus=turnus or self.turnus, actor_id=self.user.id,
            actor_label="Detail Reader", action=action, outcome="success",
            resource_type=resource_type or (
                "child" if action == "kid.edit" else "happy_cleaning"
            ),
            resource_id="27", resource_label=resource_label,
            request_id=request_id, client_ip="192.0.2.10",
            user_agent="Source Browser",
            details={} if details is None else details,
        )

    def url(self, event_id):
        return f"/api/audit-events/{event_id}/"

    def assert_privacy_headers(self, response):
        for name, value in PRIVACY_HEADERS.items():
            self.assertEqual(response.headers.get(name), value, name)
        self.assertIn(
            "Cookie",
            {item.strip() for item in response.headers.get("Vary", "").split(",")},
        )

    def test_positive_id_url_is_registered_for_get(self):
        try:
            match = resolve(self.url(41))
        except Resolver404:
            self.fail("audit event detail URL is not registered")
        self.assertEqual(match.url_name, "audit-event-detail-api")

    def test_zero_negative_and_nondigit_paths_do_not_resolve_or_touch_audit(self):
        before = AuditEvent.objects.count()
        with mock.patch.object(
            audit_views, "serialize_audit_event", create=True,
        ) as serializer:
            for value in ("0", "-1", "not-an-id"):
                with self.subTest(value=value):
                    with self.assertRaises(Resolver404):
                        resolve(self.url(value))
                    with CaptureQueriesContext(connection) as queries:
                        response = self.client.get(self.url(value))
                    self.assertEqual(response.status_code, 404)
                    self.assertFalse(any(
                        'budo_app_auditevent' in query["sql"]
                        for query in queries.captured_queries
                    ))
        serializer.assert_not_called()
        self.assertEqual(AuditEvent.objects.count(), before)

    def test_over_bigint_positive_id_is_safe_identical_404_without_lookup(self):
        huge_id = 9_223_372_036_854_775_808
        try:
            match = resolve(self.url(huge_id))
        except Resolver404:
            self.fail("syntactically positive oversized ID must reach detail policy")
        self.assertEqual(match.url_name, "audit-event-detail-api")

        with self.assertLogs(
            "budo_app.audit_policy", level="WARNING",
        ) as missing_logs:
            missing = self.client.get(self.url(999_999))
        before = AuditEvent.objects.count()
        with CaptureQueriesContext(connection) as queries, mock.patch.object(
            audit_views, "serialize_audit_event", create=True,
        ) as serializer, self.assertLogs(
            "budo_app.audit_policy", level="WARNING",
        ) as huge_logs:
            huge = self.client.get(self.url(huge_id))

        expected_log = (
            "WARNING:budo_app.audit_policy:"
            f"audit_access_denied actor_id={self.user.id} endpoint=detail "
            "reason=scope_unavailable"
        )
        self.assertEqual(missing_logs.output, [expected_log])
        self.assertEqual(huge_logs.output, [expected_log])
        self.assertEqual(huge.status_code, 404)
        self.assertEqual(huge.content, missing.content)
        self.assertFalse(any(
            'budo_app_auditevent' in query["sql"]
            for query in queries.captured_queries
        ))
        serializer.assert_not_called()
        self.assertEqual(AuditEvent.objects.count(), before)
        self.assert_privacy_headers(huge)

    def test_later_list_uses_kind_specific_value_free_detail_access_summary(self):
        access = AuditEvent.objects._create_validated_event(
            turnus=self.turnus, actor_id=self.user.id,
            actor_label="Detail Reader", action="audit.view", outcome="success",
            resource_type="audit_event", resource_id="41",
            resource_label="Audit event 41", request_id="stored-detail-access",
            client_ip=None, user_agent="tests",
            details={
                "view_kind": "detail", "result_count": 1, "filter_count": 0,
                "audit_event_id": 41, "snapshot_id": 41,
                "sensitive_payload_count": 1,
            },
        )
        response = self.client.get(
            "/api/route-data/audit-events/", {"snapshot_id": access.id},
        )

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json()["events"]
                   if item["id"] == access.id)
        self.assertNotIn("details", row)
        self.assertEqual(row["details_summary"], {
            "sensitive": False,
            "available_fields": [
                "audit_event_id", "filter_count", "result_count",
                "sensitive_payload_count", "snapshot_id", "view_kind",
            ],
        })

    def test_get_loads_one_complete_row_without_recording_a_view(self):
        target_details = valid_details()
        target = self.event(
            action="kid.edit", details=target_details,
            request_id="target", resource_label="Target child",
        )
        adjacent = self.event(
            action="kid.edit",
            details={**valid_details(), "result": "ADJACENT-SECRET"},
            request_id="adjacent", resource_label="Adjacent secret row",
        )
        with mock.patch.object(
            audit_views, "serialize_audit_event", create=True,
            wraps=serialize_audit_event,
        ) as serializer:
            response = self.client.get(
                self.url(target.id), HTTP_X_REQUEST_ID="detail-access",
                HTTP_USER_AGENT="Audit Detail/1.0", REMOTE_ADDR="192.0.2.44",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, serialize_audit_event(target))
        self.assertNotIn(adjacent.resource_label, response.content.decode())
        self.assertNotIn("ADJACENT-SECRET", response.content.decode())
        serializer.assert_called_once()
        self.assertEqual(serializer.call_args.args[0].id, target.id)
        self.assertFalse(AuditEvent.objects.filter(action="audit.view").exists())
        self.assert_privacy_headers(response)

    def test_legacy_detail_does_not_record_an_audit_view(self):
        target = self.event(
            details={"station_name": "Complete legacy value"},
            request_id="legacy-target",
        )
        before = AuditEvent.objects.count()
        response = self.client.get(self.url(target.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["details"], target.details)
        self.assertEqual(AuditEvent.objects.count(), before)
        self.assertFalse(AuditEvent.objects.filter(action="audit.view").exists())
        self.assert_privacy_headers(response)

    def test_anonymous_and_forbidden_are_logged_before_lookup_or_serialization(self):
        target = self.event(resource_label="MUST-NOT-BE-READ")
        cases = []
        self.client.logout()
        cases.append(("anonymous", None, "authentication_required"))
        forbidden = User.objects.create(username="forbidden-detail", is_staff=False)
        forbidden.user_permissions.add(self.permission)
        cases.append(("forbidden", forbidden, "forbidden"))
        for label, user, reason in cases:
            with self.subTest(label=label):
                if user is None:
                    self.client.logout()
                    actor_id = None
                else:
                    self.client.force_login(user)
                    actor_id = user.id
                with CaptureQueriesContext(connection) as queries, mock.patch.object(
                    audit_views, "serialize_audit_event", create=True,
                ) as serializer, self.assertLogs(
                    "budo_app.audit_policy", level="WARNING",
                ) as logs:
                    response = self.client.get(self.url(target.id))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(logs.output, [
                    "WARNING:budo_app.audit_policy:"
                    f"audit_access_denied actor_id={actor_id} endpoint=detail "
                    f"reason={reason}"
                ])
                serializer.assert_not_called()
                self.assertFalse(any(
                    'budo_app_auditevent' in query["sql"]
                    for query in queries.captured_queries
                ))
                self.assertNotIn("MUST-NOT-BE-READ", response.content.decode())
                self.assert_privacy_headers(response)

    def test_ordinary_foreign_and_missing_ids_share_safe_scoped_404(self):
        foreign = self.event(
            turnus=self.other_turnus, request_id="foreign",
            resource_label="FOREIGN-SECRET-LABEL",
        )
        responses = []
        with mock.patch.object(
            audit_views, "serialize_audit_event", create=True,
        ) as serializer:
            for event_id in (foreign.id, 999_999):
                with self.subTest(event_id=event_id):
                    with self.assertLogs(
                        "budo_app.audit_policy", level="WARNING",
                    ) as logs:
                        response = self.client.get(self.url(event_id))
                    self.assertEqual(logs.output, [
                        "WARNING:budo_app.audit_policy:"
                        f"audit_access_denied actor_id={self.user.id} "
                        "endpoint=detail reason=scope_unavailable"
                    ])
                    self.assertNotIn(
                        "FOREIGN-SECRET-LABEL", " ".join(logs.output),
                    )
                    self.assertNotIn(
                        f"event_id={event_id}", " ".join(logs.output),
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assert_privacy_headers(response)
                    responses.append(response.content)
        serializer.assert_not_called()
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0], responses[1])

    def test_staff_superuser_can_use_only_an_explicit_other_turnus(self):
        foreign = self.event(
            turnus=self.other_turnus, request_id="superuser-other",
        )
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])

        implicit = self.client.get(self.url(foreign.id))
        explicit = self.client.get(
            self.url(foreign.id), {"turnus": self.other_turnus.id},
        )

        self.assertEqual(implicit.status_code, 404)
        self.assertEqual(explicit.status_code, 200)
        self.assertEqual(explicit.json()["id"], foreign.id)
        self.assertFalse(AuditEvent.objects.filter(action="audit.view").exists())
        self.assert_privacy_headers(implicit)
        self.assert_privacy_headers(explicit)

class AuditViewDetailSchemaTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.data = AuditEventData(
            turnus=self.turnus, actor_id=7, actor_label="Detail Reader",
            action="audit.view", outcome="success", resource_type="audit_event",
            resource_id="41", resource_label="Audit event 41",
            request_id="detail-view", client_ip=None, user_agent="tests",
            details={
                "view_kind": "detail", "result_count": 1, "filter_count": 0,
                "audit_event_id": 41, "snapshot_id": 41,
                "sensitive_payload_count": 1,
            },
        )

    def test_detail_schema_and_envelope_are_strict(self):
        try:
            created = record_audit_event(self.data)
        except ValidationError as error:
            self.fail(f"valid audit.view detail metadata was rejected: {error}")
        self.assertEqual(created.details, self.data.details)
        non_sensitive = record_audit_event(replace(
            self.data, request_id="detail-view-nonsensitive",
            details={**self.data.details, "sensitive_payload_count": 0},
        ))
        self.assertEqual(non_sensitive.details["sensitive_payload_count"], 0)

        invalid = (
            {**self.data.details, "extra": 1},
            {key: value for key, value in self.data.details.items()
             if key != "audit_event_id"},
            {**self.data.details, "view_kind": "list"},
            {**self.data.details, "result_count": 0},
            {**self.data.details, "filter_count": 1},
            {**self.data.details, "audit_event_id": 0},
            {**self.data.details, "audit_event_id": True, "snapshot_id": True},
            {**self.data.details, "snapshot_id": 42},
            {**self.data.details, "sensitive_payload_count": 2},
        )
        accepted = []
        for index, details in enumerate(invalid):
            try:
                record_audit_event(replace(
                    self.data, request_id=f"invalid-detail-{index}", details=details,
                ))
            except ValidationError:
                continue
            accepted.append(index)
        self.assertEqual(accepted, [])

        for resource_type, resource_id in (
            ("audit_log", "41"), ("audit_event", "42"),
        ):
            with self.subTest(resource_type=resource_type, resource_id=resource_id), \
                    self.assertRaises(ValidationError):
                record_audit_event(replace(
                    self.data, request_id=f"invalid-envelope-{resource_type}",
                    resource_type=resource_type, resource_id=resource_id,
                ))
