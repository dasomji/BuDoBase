from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Auslagerorte, Tag, Turnus


class PlaceTagManagementTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 7, 1))
        self.user = User.objects.create_user(username="tag-manager", password="secret")
        approve_and_select_turnus(self.user.profil.user, turnus)
        self.user.profil.save()
        select_turnus(self.user, turnus)
        self.client.force_login(self.user)
        self.settings_url = reverse(
            "route-data-api", kwargs={"contract_key": "place-tag-settings"}
        )

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_settings_and_writes_require_tag_permissions(self):
        self.assertEqual(self.client.get(self.settings_url).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("place-tag-create-api"),
                {"name": "Wald", "icon": "trees"},
                content_type="application/json",
            ).status_code,
            403,
        )

        self.grant("change_tag")
        created = self.client.post(
            reverse("place-tag-create-api"),
            {"name": "Wald", "icon": "trees"},
            content_type="application/json",
        )

        self.assertEqual(created.status_code, 201, created.json())
        self.assertEqual(created.json()["tag"]["icon"], "trees")
        settings = self.client.get(self.settings_url)
        self.assertEqual(settings.status_code, 200)
        self.assertEqual(settings.json()["tags"], [{
            **created.json()["tag"],
            "places": [],
        }])
        self.assertEqual(len(settings.json()["icon_choices"]), 100)
        self.assertIn(
            {"value": "tent-tree", "label": "Zeltplatz"},
            settings.json()["icon_choices"],
        )
        self.assertIn(
            {"value": "flame-kindling", "label": "Lagerfeuer"},
            settings.json()["icon_choices"],
        )
        self.assertEqual(
            self.client.post(
                reverse("place-tag-delete-api", args=[created.json()["tag"]["id"]]),
                {},
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_lizardtail_https_origin_accepts_bootstrap_csrf_token_on_any_port(self):
        self.grant("change_tag")
        tag = Tag.objects.create(name="Wald", icon="trees")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        proxy_headers = {
            "HTTP_X_FORWARDED_HOST": "coolify.tailf5ea68.ts.net:8478",
            "HTTP_X_FORWARDED_PROTO": "https",
        }
        csrf_token = csrf_client.get(
            reverse("bootstrap-api"),
            **proxy_headers,
        ).json()["csrf_token"]

        response = csrf_client.post(
            reverse("place-tag-update-api", args=[tag.id]),
            {"name": "Mischwald", "icon": "trees"},
            content_type="application/json",
            HTTP_ORIGIN="https://coolify.tailf5ea68.ts.net:8478",
            HTTP_X_CSRFTOKEN=csrf_token,
            **proxy_headers,
        )

        self.assertEqual(response.status_code, 200, response.content)

    def test_settings_lists_places_for_each_tag_in_name_order(self):
        self.grant("change_tag")
        tag = Tag.objects.create(name="Wald", icon="trees")
        zelt = Auslagerorte.objects.create(name="Zeltplatz")
        alm = Auslagerorte.objects.create(name="Almhütte")
        zelt.tags.add(tag)
        alm.tags.add(tag)

        response = self.client.get(self.settings_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tags"][0]["places"], [
            {"id": alm.id, "name": "Almhütte"},
            {"id": zelt.id, "name": "Zeltplatz"},
        ])

    def test_delete_detaches_tag_and_promotes_a_remaining_tag(self):
        self.grant("change_tag", "delete_tag")
        primary = Tag.objects.create(name="Zeltplatz", icon="tent-tree")
        remaining = Tag.objects.create(name="Wald", icon="trees")
        place = Auslagerorte.objects.create(name="Lager")
        place.tags.set([primary, remaining])
        place.primary_tag = primary
        place.save(update_fields=["primary_tag"])

        response = self.client.post(
            reverse("place-tag-delete-api", args=[primary.id]),
            {},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.json())
        place.refresh_from_db()
        self.assertEqual(list(place.tags.all()), [remaining])
        self.assertEqual(place.primary_tag, remaining)

    def test_invalid_icon_and_case_insensitive_duplicate_are_rejected(self):
        self.grant("change_tag")
        Tag.objects.create(name="Wald")
        invalid = self.client.post(
            reverse("place-tag-create-api"),
            {"name": "See", "icon": "unknown"},
            content_type="application/json",
        )
        duplicate = self.client.post(
            reverse("place-tag-create-api"),
            {"name": " wALD ", "icon": "trees"},
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(duplicate.status_code, 409)
