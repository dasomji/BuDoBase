"""Browser-shell contract for the protected Audit-Log route (#168)."""

from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import Resolver404, resolve, reverse

from budo_app.models import Turnus


class AuditPageRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        cls.view_permission = Permission.objects.get(codename="view_auditevent")
        cls.export_permission = Permission.objects.get(codename="export_auditevent")

    def user(self, username, *, staff, permissions=(), active_turnus=True,
             superuser=False):
        user = User.objects.create_user(
            username=username,
            password="secret",
            is_staff=staff,
            is_superuser=superuser,
        )
        user.user_permissions.add(*permissions)
        if active_turnus:
            user.profil.turnus = self.turnus
            user.profil.save(update_fields=["turnus"])
        return user

    def assert_no_shell(self, response):
        rendered = response.content.decode()
        self.assertNotIn('<div id="root">', rendered)
        self.assertNotIn("/static/frontend/app.js", rendered)

    def test_explicit_canonical_route_is_named_and_neighbor_is_not_captured(self):
        self.assertEqual(reverse("audit-page"), "/audit/")
        self.assertEqual(resolve("/audit/").url_name, "audit-page")
        with self.assertRaises(Resolver404):
            resolve("/audit-settings/")

    def test_anonymous_redirect_preserves_full_path_and_query_without_shell(self):
        response = self.client.get("/audit/", {"actor": "Ada"})

        self.assertEqual(response.status_code, 302)
        redirect = urlsplit(response.url)
        self.assertEqual(redirect.path, "/login/")
        self.assertEqual(parse_qs(redirect.query), {"next": ["/audit/?actor=Ada"]})
        self.assert_no_shell(response)

    def test_slashless_request_redirects_to_the_single_canonical_route(self):
        user = self.user(
            "slash-reader",
            staff=True,
            permissions=(self.view_permission,),
        )
        self.client.force_login(user)

        response = self.client.get("/audit", {"actor": "Ada"})

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/audit/?actor=Ada")

    def test_nonstaff_with_both_permissions_and_staff_without_view_are_denied_before_shell(self):
        actors = (
            self.user(
                "raw-permissions",
                staff=False,
                permissions=(self.view_permission, self.export_permission),
            ),
            self.user("staff-without-view", staff=True),
            self.user("nonstaff-superuser", staff=False, superuser=True),
        )
        for actor in actors:
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                response = self.client.get("/audit/")
                self.assertEqual(response.status_code, 403)
                self.assert_no_shell(response)

    def test_view_authorized_staff_gets_only_the_shell_with_no_turnus_requirement(self):
        user = self.user(
            "shell-reader",
            staff=True,
            permissions=(self.view_permission,),
            active_turnus=False,
        )
        self.client.force_login(user)

        response = self.client.get("/audit/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)
        self.assertContains(response, "/static/frontend/app.js")
        self.assertNotContains(response, '"before"')
        self.assertNotContains(response, '"after"')

    def test_route_is_get_only_and_staff_superuser_uses_the_same_policy(self):
        user = self.user(
            "staff-superuser",
            staff=True,
            superuser=True,
            active_turnus=False,
        )
        self.client.force_login(user)

        self.assertEqual(self.client.get("/audit/").status_code, 200)
        post = self.client.post("/audit/")
        self.assertEqual(post.status_code, 405)
        self.assert_no_shell(post)
