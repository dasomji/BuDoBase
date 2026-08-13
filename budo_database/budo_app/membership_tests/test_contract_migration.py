from datetime import date

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Kinder, Profil, Turnus


class LegacyProfileAuthorityContractTests(TestCase):
    def test_membership_scopes_kids_after_legacy_profile_authority_is_removed(self):
        selected = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        foreign = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 15),
        )
        user = User.objects.create_user(username="contracted-profile")
        create_membership(user=user, turnus=selected)
        select_turnus(user, selected)
        selected_child = Kinder.objects.create(
            kid_index="SELECTED-1",
            kid_vorname="Selected",
            kid_nachname="Member",
            turnus=selected,
        )
        Kinder.objects.create(
            kid_index="FOREIGN-1",
            kid_vorname="Foreign",
            kid_nachname="Child",
            turnus=foreign,
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "kids-directory"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [kid["id"] for kid in response.json()["kids"]],
            [selected_child.pk],
        )
        self.assertNotIn("turnus", {field.name for field in Profil._meta.get_fields()})
        self.assertNotIn("rolle", {field.name for field in Profil._meta.get_fields()})
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, Profil._meta.db_table
                )
            }
        self.assertNotIn("turnus_id", columns)
        self.assertNotIn("rolle", columns)
