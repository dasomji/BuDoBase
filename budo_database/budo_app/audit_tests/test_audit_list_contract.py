"""RED contract for stable, metadata-only audit list reads (#164-05)."""

import json
from dataclasses import replace
from datetime import date
from unittest import mock
from unittest import skipUnless

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from budo_app.audit import (
    ACTION_DETAIL_FIELDS,
    MAX_DETAILS_BYTES,
    AuditEventData,
    record_audit_event,
)
from budo_app.audit_queries import FILTER_NAMES
from budo_app.audit_tests.test_kid_edit_audit_schema import valid_details
from budo_app.models import AuditEvent, Turnus
from budo_app.read_contracts.registry import get_contract


PRIVACY_HEADERS = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class AuditListContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create(username="audit-list-reader", is_staff=True)
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_auditevent"),
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        self.client.force_login(self.user)
        self.url = reverse(
            "route-data-api", kwargs={"contract_key": "audit-events"},
        )

    def event(self, *, action="happy_cleaning.event.create", details=None,
              request_id=None, turnus=None, outcome="success",
              resource_type="happy_cleaning"):
        return AuditEvent.objects._create_validated_event(
            turnus=turnus or self.turnus, actor_id=self.user.id,
            actor_label="Audit Reader", action=action, outcome=outcome,
            resource_type=resource_type, resource_id="41",
            resource_label="Happy Cleaning 1",
            request_id=request_id or f"source-{AuditEvent.objects.count() + 1}",
            client_ip="192.0.2.10", user_agent="Source Browser",
            details={} if details is None else details,
        )

    def assert_privacy_headers(self, response):
        for name, value in PRIVACY_HEADERS.items():
            self.assertEqual(response.headers.get(name), value, name)
        self.assertIn(
            "Cookie",
            {item.strip() for item in response.headers.get("Vary", "").split(",")},
        )

    def test_snapshot_is_captured_reused_and_rejects_invalid_values(self):
        oldest = self.event(request_id="oldest")
        middle = self.event(request_id="middle")
        newest = self.event(request_id="newest")

        first = self.client.get(self.url, {"page": 1, "page_size": 1})
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertIn("snapshot_id", first_payload["pagination"])
        self.assertEqual(first_payload["pagination"]["snapshot_id"], newest.id)
        self.assertEqual([row["id"] for row in first_payload["events"]], [newest.id])
        self.assertTrue(all(
            row["id"] <= newest.id for row in first_payload["events"]
        ))

        appended = self.event(request_id="appended-after-page-one")
        second = self.client.get(self.url, {
            "page": 2, "page_size": 1, "snapshot_id": newest.id,
        })
        second_payload = second.json()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second_payload["pagination"]["snapshot_id"], newest.id)
        self.assertEqual(second_payload["pagination"]["total"], 3)
        self.assertEqual([row["id"] for row in second_payload["events"]], [middle.id])
        self.assertNotIn(appended.id, {
            row["id"] for row in first_payload["events"] + second_payload["events"]
        })
        self.assertLess(oldest.id, middle.id)

        sentinel = self.client.get(self.url, {"snapshot_id": "0"})
        self.assertEqual(sentinel.status_code, 200)
        self.assertEqual(sentinel.json()["pagination"]["snapshot_id"], 0)
        self.assertEqual(sentinel.json()["events"], [])

        current_max = AuditEvent.objects.filter(turnus=self.turnus).latest("id").id
        for value in ("-1", "not-an-integer", str(current_max + 1)):
            with self.subTest(snapshot_id=value):
                before = AuditEvent.objects.filter(action="audit.view").count()
                response = self.client.get(self.url, {"snapshot_id": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    AuditEvent.objects.filter(action="audit.view").count(), before,
                )

    def test_every_action_is_summary_only_and_kid_edit_summary_is_exact(self):
        actions = sorted(set(ACTION_DETAIL_FIELDS) - {"audit.view"})
        for action in actions:
            details = (
                {"station_name": "LEGACY-FULL-DETAIL-SECRET"}
                if action == "happy_cleaning.event.create" else {}
            )
            self.event(action=action, details=details, request_id=f"legacy-{action}")
        kid_details = valid_details()
        kid = self.event(action="kid.edit", details=kid_details, request_id="kid-edit")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url, {"page_size": 100})
        self.assertEqual(response.status_code, 200)
        audit_selects = [
            query["sql"] for query in queries.captured_queries
            if query["sql"].lstrip().upper().startswith("SELECT")
            and 'FROM "budo_app_auditevent"' in query["sql"]
        ]
        self.assertTrue(audit_selects)
        self.assertFalse(any(
            '"budo_app_auditevent"."details",' in sql
            or sql.split(" FROM ", 1)[0].rstrip().endswith(
                '"budo_app_auditevent"."details"'
            )
            for sql in audit_selects
        ), "the list query must not load complete audit details JSON")
        rows = response.json()["events"]
        self.assertEqual({row["action"] for row in rows}, set(actions) | {"kid.edit"})
        self.assertNotIn("LEGACY-FULL-DETAIL-SECRET", response.content.decode())
        legacy_summaries = {}
        for row in rows:
            with self.subTest(action=row["action"]):
                self.assertNotIn("details", row)
                self.assertIn("details_summary", row)
                self.assertLessEqual(len(json.dumps(row["details_summary"])), 1024)
                self.assertEqual(
                    row["details_url"], f"/api/audit-events/{row['id']}/",
                )
                self.assertEqual(
                    [key for key in row if key.endswith("_url")], ["details_url"],
                )
                if row["action"] != "kid.edit":
                    legacy_summaries[row["action"]] = row["details_summary"]
        self.assertEqual(legacy_summaries, {
            action: {
                "sensitive": False,
                "available_fields": sorted(ACTION_DETAIL_FIELDS[action]),
            }
            for action in actions
        })
        kid_row = next(row for row in rows if row["id"] == kid.id)
        self.assertEqual(kid_row["details_summary"], {
            "schema": "budo.kid-edit",
            "version": 1,
            "result": kid_details["result"],
            "changed_paths": kid_details["changed_paths"],
            "sensitive": True,
        })
        self.assert_privacy_headers(response)

    def test_successful_list_does_not_record_an_audit_view(self):
        source = self.event(request_id="source")
        before = AuditEvent.objects.count()

        response = self.client.get(
            self.url,
            {"action": source.action, "outcome": "success", "page_size": 1},
            HTTP_X_REQUEST_ID="audit-list-access-request",
            HTTP_USER_AGENT="Audit Explorer/1.0",
            REMOTE_ADDR="192.0.2.44",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuditEvent.objects.count(), before)
        self.assertFalse(AuditEvent.objects.filter(action="audit.view").exists())
        self.assertNotIn("details", response.json()["events"][0])
        self.assert_privacy_headers(response)

    def test_unrelated_audit_builder_runtime_error_remains_visible(self):
        unrelated = RuntimeError("unrelated builder defect")
        contract = replace(
            get_contract("audit-events"), builder=mock.Mock(side_effect=unrelated),
        )
        with mock.patch(
            "budo_app.read_contracts.views.get_contract", return_value=contract,
        ), self.assertRaisesRegex(RuntimeError, "unrelated builder defect"):
            self.client.get(self.url)

    def test_denials_have_the_exact_list_privacy_headers(self):
        other = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        cases = []
        self.client.logout()
        cases.append(("anonymous", self.client.get(self.url), 403))
        nonstaff = User.objects.create(username="nonstaff")
        nonstaff.user_permissions.add(
            Permission.objects.get(codename="view_auditevent"),
        )
        self.client.force_login(nonstaff)
        cases.append(("authenticated-forbidden", self.client.get(self.url), 403))
        self.client.force_login(self.user)
        cases.append((
            "scope-unavailable",
            self.client.get(self.url, {"turnus": other.id}),
            404,
        ))
        for label, response, status in cases:
            with self.subTest(label=label):
                self.assertEqual(response.status_code, status)
                self.assert_privacy_headers(response)

    def test_explicit_superuser_scope_is_kept_on_details_url(self):
        other = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        event = self.event(turnus=other, request_id="other-turnus")
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])

        response = self.client.get(self.url, {"turnus": other.id})

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json()["events"] if item["id"] == event.id)
        self.assertEqual(
            row["details_url"],
            f"/api/audit-events/{event.id}/?turnus={other.id}",
        )

    def test_filter_options_are_capped_at_the_reused_snapshot(self):
        snapshot = self.event(request_id="snapshot")
        self.event(
            action="happy_cleaning.todo.create", outcome="forbidden",
            resource_type="future_type", request_id="after-snapshot",
        )

        response = self.client.get(self.url, {"snapshot_id": snapshot.id})

        self.assertEqual(response.status_code, 200)
        options = response.json()["filter_options"]
        self.assertNotIn("happy_cleaning.todo.create", options["actions"])
        self.assertNotIn("forbidden", options["outcomes"])
        self.assertNotIn("future_type", options["resource_types"])

    def test_malformed_stored_kid_schema_or_version_fails_closed(self):
        for index, mutation in enumerate((
            {"schema": "forged.schema"}, {"version": 2},
        ), start=10):
            with self.subTest(mutation=mutation):
                turnus = Turnus.objects.create(
                    turnus_nr=index, turnus_beginn=date(2026, 9, 1),
                )
                self.user.profil.turnus = turnus
                self.user.profil.save(update_fields=["turnus"])
                details = {**valid_details(), **mutation}
                self.event(
                    action="kid.edit", details=details, turnus=turnus,
                    request_id=f"MALFORMED-{index}",
                )
                self.client.raise_request_exception = False
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("events", response.json())
                self.assertNotIn("MALFORMED", response.content.decode())
                self.assert_privacy_headers(response)

    @skipUnless(connection.vendor == "sqlite", "default-SQLite portability check")
    def test_list_summary_query_runs_on_default_sqlite(self):
        event = self.event(request_id="sqlite-portable")
        try:
            response = self.client.get(self.url)
        except Exception as error:  # pragma: no cover - converts backend error to RED
            self.fail(f"audit list query is not SQLite-portable: {error}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["events"][0]["id"], event.id)


class AuditViewListSchemaTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.data = AuditEventData(
            turnus=self.turnus, actor_id=7, actor_label="Audit Reader",
            action="audit.view", outcome="success", resource_type="audit_log",
            resource_id=str(self.turnus.id), resource_label=str(self.turnus),
            request_id="audit-list-view", client_ip=None, user_agent="tests",
            details={
                "view_kind": "list", "result_count": 50, "filter_count": 2,
                "page": 1, "page_size": 50, "snapshot_id": 811,
                "sensitive_payload_count": 0,
            },
        )

    def test_list_schema_and_outer_resource_are_exact(self):
        try:
            created = record_audit_event(self.data)
        except ValidationError as error:
            self.fail(f"valid audit.view list metadata was rejected: {error}")
        self.assertEqual(created.details, self.data.details)
        self.assertLessEqual(
            len(json.dumps(created.details, separators=(",", ":")).encode()),
            MAX_DETAILS_BYTES,
        )
        self.assertEqual(
            (created.resource_type, created.resource_id),
            ("audit_log", str(self.turnus.id)),
        )

        invalid = (
            {**self.data.details, "extra": 1},
            {key: value for key, value in self.data.details.items() if key != "page"},
            {**self.data.details, "view_kind": "detail"},
            {**self.data.details, "result_count": -1},
            {**self.data.details, "filter_count": True},
            {**self.data.details, "page": 0},
            {**self.data.details, "page_size": 0},
            {**self.data.details, "snapshot_id": -1},
            {**self.data.details, "sensitive_payload_count": 1},
            {**self.data.details, "view_kind": "x" * (MAX_DETAILS_BYTES + 1)},
            {**self.data.details, "result_count": 101, "page_size": 100},
            {**self.data.details, "filter_count": len(FILTER_NAMES) + 1},
            {**self.data.details, "page_size": 101},
            {**self.data.details, "page": 9_223_372_036_854_775_808},
            {**self.data.details, "snapshot_id": 9_223_372_036_854_775_808},
        )
        accepted_invalid = []
        for index, details in enumerate(invalid):
            try:
                record_audit_event(replace(
                    self.data, request_id=f"invalid-{index}", details=details,
                ))
            except ValidationError:
                continue
            accepted_invalid.append(index)

        upper = replace(self.data, request_id="valid-upper", details={
            **self.data.details,
            "result_count": 100,
            "filter_count": len(FILTER_NAMES),
            "page": 9_223_372_036_854_775_807,
            "page_size": 100,
            "snapshot_id": 9_223_372_036_854_775_807,
        })
        record_audit_event(upper)
        self.assertEqual(
            accepted_invalid, [],
            f"invalid audit.view range/schema cases accepted: {accepted_invalid}",
        )

        for resource_type, resource_id in (
            ("audit_event", str(self.turnus.id)),
            ("audit_log", str(self.turnus.id + 1)),
        ):
            with self.subTest(resource_type=resource_type, resource_id=resource_id), \
                    self.assertRaises(ValidationError):
                record_audit_event(replace(
                    self.data, request_id=f"bad-envelope-{resource_type}",
                    resource_type=resource_type, resource_id=resource_id,
                ))
