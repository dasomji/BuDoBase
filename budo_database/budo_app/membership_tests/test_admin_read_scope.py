from datetime import date

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Kinder, Notizen, Turnus


class AdminReadScopeTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.first = Turnus.objects.create(
            turnus_nr=1, turnus_beginn=date(2026, 7, 1)
        )
        self.second = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 15)
        )
        self.staff = User.objects.create_user(username="staff", is_staff=True)
        create_membership(user=self.staff, turnus=self.first)
        select_turnus(self.staff, self.first)
        first_kid = Kinder.objects.create(
            kid_index="first", kid_vorname="First", kid_nachname="Kid",
            turnus=self.first,
        )
        second_kid = Kinder.objects.create(
            kid_index="second", kid_vorname="Second", kid_nachname="Kid",
            turnus=self.second,
        )
        self.first_note = Notizen.objects.create(
            kinder=first_kid, notiz="first", added_by=self.staff
        )
        self.second_note = Notizen.objects.create(
            kinder=second_kid, notiz="second", added_by=self.staff
        )
        self.model_admin = admin.site._registry[Notizen]

    def request_for(self, user):
        request = self.factory.get("/admin/budo_app/notizen/")
        request.user = user
        return request

    def test_staff_queryset_and_object_permission_require_selected_membership(self):
        request = self.request_for(self.staff)

        self.assertEqual(list(self.model_admin.get_queryset(request)), [self.first_note])
        self.assertTrue(self.model_admin.has_view_permission(request, self.first_note))
        self.assertFalse(self.model_admin.has_view_permission(request, self.second_note))

        self.staff.turnus_memberships.all().delete()
        self.assertFalse(self.model_admin.get_queryset(request).exists())
        self.assertFalse(self.model_admin.has_view_permission(request, self.first_note))

    def test_superuser_retains_global_admin_read_access(self):
        superuser = User.objects.create_superuser(username="root", password="secret")
        request = self.request_for(superuser)

        self.assertCountEqual(
            self.model_admin.get_queryset(request),
            [self.first_note, self.second_note],
        )
        self.assertTrue(self.model_admin.has_view_permission(request, self.second_note))
