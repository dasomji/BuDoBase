from datetime import date
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.http import QueryDict
from django.urls import reverse

from budo_app.forms import AuslagerForm
from budo_app.models import Auslagerorte, Tag, Turnus


class PlaceTagContractTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="place-tag-user",
            password="secret",
        )
        self.user.profil.turnus = turnus
        self.user.profil.save()
        self.client.force_login(self.user)

    def contract_url(self, key, place=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={place.id}" if place else url

    def submit_place(self, target, *, name, tags):
        with patch(
            "budo_app.auslagerorte_views.update_auslagerorte_coordinates",
            side_effect=lambda place: place,
        ):
            return self.client.post(
                reverse("form-submit-api"),
                {
                    "_target": target,
                    "name": name,
                    "land": "Österreich",
                    "tags": tags,
                },
            )

    def test_inline_tags_round_trip_through_create_and_reuse_names_case_insensitively(self):
        first = self.submit_place(
            "/auslagerorte/create",
            name="Badesee",
            tags=["  Badeplatz  ", "Schlechtwetter   tauglich"],
        )
        second = self.submit_place(
            "/auslagerorte/create",
            name="Hallenbad",
            tags=["bADEPLATZ"],
        )

        self.assertEqual(first.status_code, 200, first.json())
        self.assertEqual(second.status_code, 200, second.json())
        response = self.client.get(self.contract_url("places-list"))
        places = {place["name"]: place for place in response.json()["places"]}

        self.assertEqual(
            places["Badesee"]["tags"],
            ["Badeplatz", "Schlechtwetter tauglich"],
        )
        self.assertEqual(places["Hallenbad"]["tags"], ["Badeplatz"])
        self.assertEqual(
            response.json()["available_tags"],
            ["Badeplatz", "Schlechtwetter tauglich"],
        )

    def test_update_replaces_removed_tags_and_contracts_expose_available_names(self):
        created = self.submit_place(
            "/auslagerorte/create",
            name="Waldhütte",
            tags=["Badeplatz", "Schlechtwetter tauglich"],
        )
        self.assertEqual(created.status_code, 200, created.json())
        place = Auslagerorte.objects.get(name="Waldhütte")

        updated = self.submit_place(
            f"/auslagerorte/{place.id}/update",
            name="Waldhütte",
            tags=["  Wanderung  "],
        )

        self.assertEqual(updated.status_code, 200, updated.json())
        list_payload = self.client.get(
            self.contract_url("places-list"),
        ).json()
        detail_payload = self.client.get(
            self.contract_url("place-detail", place),
        ).json()
        create_payload = self.client.get(
            self.contract_url("place-create"),
        ).json()
        update_payload = self.client.get(
            self.contract_url("place-update", place),
        ).json()

        self.assertEqual(list_payload["places"][0]["tags"], ["Wanderung"])
        self.assertEqual(list_payload["available_tags"], ["Wanderung"])
        self.assertEqual(detail_payload["places"][0]["tags"], ["Wanderung"])
        self.assertEqual(update_payload["places"][0]["tags"], ["Wanderung"])
        self.assertEqual(
            create_payload["available_tags"],
            ["Badeplatz", "Schlechtwetter tauglich", "Wanderung"],
        )
        self.assertEqual(
            update_payload["available_tags"],
            ["Badeplatz", "Schlechtwetter tauglich", "Wanderung"],
        )

    def test_save_recovers_when_a_concurrent_writer_creates_the_same_tag(self):
        existing = Tag.objects.create(name="Wanderung")
        data = QueryDict(mutable=True)
        data.update({"name": "Waldhütte"})
        data.setlist("tags", ["wanderung"])
        form = AuslagerForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

        from django.db import IntegrityError

        with patch.object(Tag.objects, "get_or_create", side_effect=IntegrityError):
            place = form.save()

        self.assertEqual(list(place.tags.all()), [existing])


class TagAdminValidationTests(TestCase):
    def test_admin_form_rejects_duplicate_after_normalizing_whitespace_and_case(self):
        Tag.objects.create(name="Admin-Regressions Badeplatz See")
        tag_admin = admin.site._registry[Tag]
        form_class = tag_admin.get_form(request=None)

        form = form_class(data={"name": "  aDMIN-rEGRESSIONS   bADEPLATZ   SEE  "})

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertEqual(form.instance.name, "aDMIN-rEGRESSIONS bADEPLATZ SEE")
