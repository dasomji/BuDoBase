"""RED contract for centralized audit authorization only (#164-04)."""

from dataclasses import dataclass
from datetime import date
from unittest import mock

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from budo_app.models import AuditEvent, Turnus

try:
    from budo_app.audit_policy import (
        can_export_audit,
        can_view_audit,
        log_audit_denial,
    )
except ModuleNotFoundError as error:
    if error.name != "budo_app.audit_policy":
        raise
    can_export_audit = None
    can_view_audit = None
    log_audit_denial = None


VIEW_PERMISSION = "budo_app.view_auditevent"
EXPORT_PERMISSION = "budo_app.export_auditevent"


@dataclass
class PolicyUser:
    is_authenticated: bool
    is_active: bool
    is_staff: bool
    permissions: frozenset
    is_superuser: bool = False
    id: int = 7

    def has_perm(self, permission):
        return self.is_superuser or permission in self.permissions


class AuditPolicyUnitTests(SimpleTestCase):
    def require_policy(self):
        self.assertTrue(callable(can_view_audit), "audit_policy is not implemented")
        self.assertTrue(callable(can_export_audit))
        self.assertTrue(callable(log_audit_denial))

    def test_exact_compact_actor_matrix_including_nonstaff_permissions_and_superuser(self):
        self.require_policy()
        both = frozenset({VIEW_PERMISSION, EXPORT_PERMISSION})
        view = frozenset({VIEW_PERMISSION})
        cases = (
            (AnonymousUser(), False, False, "anonymous"),
            (PolicyUser(True, False, True, both), False, False, "inactive"),
            (PolicyUser(True, True, False, frozenset()), False, False,
             "nonstaff none"),
            (PolicyUser(True, True, False, both), False, False,
             "nonstaff permissions"),
            (PolicyUser(True, True, True, frozenset()), False, False,
             "staff none"),
            (PolicyUser(True, True, True, view), True, False,
             "staff view"),
            (PolicyUser(True, True, True, both), True, True,
             "staff both"),
            (PolicyUser(True, True, True, frozenset(), True), True, True,
             "staff superuser"),
            (PolicyUser(True, True, False, frozenset(), True), False, False,
             "nonstaff superuser anomaly"),
        )
        for user, expected_view, expected_export, label in cases:
            with self.subTest(label=label):
                self.assertIs(can_view_audit(user), expected_view)
                self.assertIs(can_export_audit(user), expected_export)

    def test_denial_log_contains_fixed_metadata_only(self):
        self.require_policy()
        user = PolicyUser(True, True, False, frozenset(), id=71)
        with self.assertLogs("budo_app.audit_policy", level="WARNING") as logs:
            result = log_audit_denial(
                user=user, endpoint_kind="list", reason_code="forbidden",
            )
        self.assertIsNone(result)
        self.assertEqual(
            logs.output,
            [
                "WARNING:budo_app.audit_policy:"
                "audit_access_denied actor_id=71 endpoint=list reason=forbidden"
            ],
        )


class AuditAuthorizationHttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        self.view_permission = Permission.objects.get(codename="view_auditevent")
        self.export_permission = Permission.objects.get(codename="export_auditevent")
        self.list_url = reverse(
            "route-data-api", kwargs={"contract_key": "audit-events"},
        )
        self.export_url = reverse("audit-export-api")
        self.other_event = AuditEvent.objects._create_validated_event(
            turnus=self.other_turnus, actor_id=9, actor_label="Other",
            action="happy_cleaning.event.create", outcome="success",
            resource_type="happy_cleaning", resource_id="1",
            resource_label="Other", request_id="other", client_ip=None,
            user_agent="tests", details={"happy_cleaning_number": 1},
        )

    def user(self, username, *, staff, permissions=(), superuser=False,
             active_turnus=True):
        user = User.objects.create(username=username)
        user.is_staff = staff
        user.is_superuser = superuser
        user.save(update_fields=["is_staff", "is_superuser"])
        user.user_permissions.add(*permissions)
        if active_turnus:
            user.profil.turnus = self.turnus
            user.profil.save(update_fields=["turnus"])
        return user

    def denied_users(self):
        return (
            self.user(
                "nonstaff-with-perms", staff=False,
                permissions=(self.view_permission, self.export_permission),
            ),
            self.user("staff-without-view", staff=True),
        )

    def test_list_denies_authenticated_actors_before_all_request_work(self):
        from budo_app.audit_queries import AuditFilters

        for user in self.denied_users():
            self.client.force_login(user)
            with self.subTest(user=user.username):
                with mock.patch(
                    "budo_app.read_contracts.domains.audit."
                    "AuditFilters.from_query_params",
                    wraps=AuditFilters.from_query_params,
                ) as parse, mock.patch(
                    "budo_app.read_contracts.domains.audit.filtered_audit_events",
                ) as query, mock.patch(
                    "budo_app.read_contracts.domains.audit.serialize_audit_list_event",
                ) as serializer:
                    response = self.client.get(
                        self.list_url,
                        {"turnus": "SECRET-TURNUS", "actor": "SECRET-FILTER"},
                    )
                parse.assert_not_called()
                query.assert_not_called()
                serializer.assert_not_called()
                self.assertEqual(response.status_code, 403)

    def test_export_denies_authenticated_actors_before_all_request_work(self):
        from budo_app.audit_exports import export_audit_events as actual_builder
        from budo_app.audit_queries import AuditFilters

        for user in self.denied_users():
            self.client.force_login(user)
            with self.subTest(user=user.username):
                with mock.patch(
                    "budo_app.audit_views.AuditFilters.from_query_params",
                    wraps=AuditFilters.from_query_params,
                ) as parse, mock.patch(
                    "budo_app.audit_views.build_audit_export",
                    wraps=actual_builder,
                ) as builder:
                    response = self.client.get(
                        self.export_url,
                        {"turnus": "SECRET-TURNUS", "actor": "SECRET-FILTER"},
                    )
                parse.assert_not_called()
                builder.assert_not_called()
                self.assertEqual(response.status_code, 403)

    def test_bootstrap_keeps_existing_permission_object_with_effective_booleans_no_logs(self):
        cases = (
            (False, (self.view_permission, self.export_permission), False, False),
            (True, (self.view_permission,), True, False),
            (True, (self.view_permission, self.export_permission), True, True),
        )
        for index, (staff, permissions, expected_view, expected_export) in enumerate(cases):
            user = self.user(f"bootstrap-{index}", staff=staff,
                             permissions=permissions)
            self.client.force_login(user)
            with self.subTest(index=index), self.assertNoLogs(
                "budo_app.audit_policy", level="WARNING",
            ):
                response = self.client.get(reverse("bootstrap-api"))
            self.assertEqual(response.status_code, 200)
            permission_payload = response.json()["permissions"]
            self.assertEqual(set(permission_payload), {
                "change_kids", "change_profiles", "change_focuses",
                "change_places", "view_auditevent", "export_auditevent",
            })
            self.assertIs(permission_payload["view_auditevent"], expected_view)
            self.assertIs(permission_payload["export_auditevent"], expected_export)

    def test_authorized_turnus_scope_is_404_or_safely_empty_never_unscoped(self):
        ordinary = self.user(
            "ordinary", staff=True, permissions=(self.view_permission,),
        )
        self.client.force_login(ordinary)
        self.assertEqual(
            self.client.get(self.list_url, {"turnus": self.turnus.pk}).status_code,
            200,
        )
        for requested in (self.other_turnus.pk, 999_999):
            with self.subTest(actor="ordinary", requested=requested), mock.patch(
                "budo_app.read_contracts.domains.audit.serialize_audit_list_event",
            ) as serializer:
                response = self.client.get(self.list_url, {"turnus": requested})
            self.assertEqual(response.status_code, 404)
            serializer.assert_not_called()

        staff_superuser = self.user(
            "staff-superuser", staff=True, superuser=True,
        )
        self.client.force_login(staff_superuser)
        response = self.client.get(
            self.list_url, {"turnus": self.other_turnus.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.other_event.id, [item["id"] for item in response.json()["events"]])

        for index, superuser in enumerate((False, True)):
            unscoped = self.user(
                f"unscoped-{index}", staff=True,
                permissions=(self.view_permission,), superuser=superuser,
                active_turnus=False,
            )
            self.client.force_login(unscoped)
            with self.subTest(superuser=superuser), mock.patch(
                "budo_app.read_contracts.domains.audit.filtered_audit_events",
            ) as query:
                response = self.client.get(self.list_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["events"], [])
            query.assert_not_called()

    def test_unavailable_explicit_list_and_export_scopes_log_fixed_metadata_before_404(self):
        user = self.user(
            "scoped-auditor", staff=True,
            permissions=(self.view_permission, self.export_permission),
        )
        self.client.force_login(user)
        scopes = (self.other_turnus.pk, 999_999, "MALFORMED-SECRET-SCOPE")
        for endpoint, url in (("list", self.list_url), ("export", self.export_url)):
            for scope in scopes:
                with self.subTest(endpoint=endpoint, scope=scope):
                    with self.assertLogs(
                        "budo_app.audit_policy", level="WARNING",
                    ) as logs:
                        response = self.client.get(
                            url,
                            {"turnus": scope, "actor": "SECRET-FILTER-VALUE"},
                        )
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(logs.output, [
                        "WARNING:budo_app.audit_policy:"
                        f"audit_access_denied actor_id={user.pk} "
                        f"endpoint={endpoint} reason=scope_unavailable"
                    ])
                    rendered = " ".join(logs.output)
                    self.assertNotIn("turnus", rendered.casefold())
                    self.assertNotIn("query", rendered.casefold())
                    self.assertNotIn("filter", rendered.casefold())
                    self.assertNotIn("SECRET", rendered)
                    self.assertNotIn("actor=", rendered)

    def test_anonymous_list_and_export_denials_log_fixed_authentication_metadata(self):
        self.client.logout()
        for endpoint, url in (("list", self.list_url), ("export", self.export_url)):
            with self.subTest(endpoint=endpoint):
                with self.assertLogs(
                    "budo_app.audit_policy", level="WARNING",
                ) as logs:
                    response = self.client.get(
                        url,
                        {"turnus": "SECRET-SCOPE", "actor": "SECRET-FILTER"},
                    )
                self.assertIn(response.status_code, {401, 403})
                self.assertEqual(logs.output, [
                    "WARNING:budo_app.audit_policy:"
                    "audit_access_denied actor_id=None "
                    f"endpoint={endpoint} reason=authentication_required"
                ])
                self.assertNotIn("SECRET", " ".join(logs.output))
