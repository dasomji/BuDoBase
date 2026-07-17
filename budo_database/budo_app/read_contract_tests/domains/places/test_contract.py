from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Turnus,
)
from budo_app.read_contract_tests.fixtures import image_upload


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


LIST_FIELDS = {
    "id",
    "name",
    "coordinates",
    "maps_link",
    "parking_link",
}

DETAIL_FIELDS = {
    "id",
    "name",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "coordinates",
    "maps_link",
    "description",
    "contact",
    "parking_link",
    "parking_coordinates",
    "images",
    "notes",
}

FORM_FIELDS = {
    "id",
    "name",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "maps_link",
    "description",
    "parking_link",
}

REFERENCE_FIELDS = {"id", "name"}


@override_settings(STORAGES=TEST_STORAGES)
class PlacesContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="places-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.place = Auslagerorte.objects.create(
            name="Ada Hütte",
            strasse="Waldweg 4",
            ort="Sallingstadt",
            bundesland="Niederösterreich",
            postleitzahl="3931",
            land="Österreich",
            koordinaten="48.5, 15.0",
            maps_link="https://maps.example.test/ada",
            maps_link_parkspot="https://maps.example.test/parking",
            koordinaten_parkspot="48.51, 15.01",
            beschreibung="Lagerplatz am Wald",
            kontakt="Ada +43 123",
        )

    def contract_url(self, key, place=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={place.id}" if place else url

    def test_list_returns_only_the_lightweight_ordered_map_projection(self):
        Auslagerorte.objects.create(name="Zeltplatz")

        response = self.client.get(self.contract_url("places-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"places"})
        self.assertEqual(
            [place["name"] for place in response.json()["places"]],
            ["Ada Hütte", "Zeltplatz"],
        )
        self.assertEqual(set(response.json()["places"][0]), LIST_FIELDS)
        self.assertEqual(
            response.json()["places"][0],
            {
                "id": self.place.id,
                "name": "Ada Hütte",
                "coordinates": "48.5, 15.0",
                "maps_link": "https://maps.example.test/ada",
                "parking_link": "https://maps.example.test/parking",
            },
        )

    def test_list_preserves_empty_behavior(self):
        Auslagerorte.objects.all().delete()

        response = self.client.get(self.contract_url("places-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"places": []})

    def test_detail_returns_one_explicit_place_with_notes_and_storage_urls(self):
        note = AuslagerorteNotizen.objects.create(
            auslagerort=self.place,
            notiz="Wasser abdrehen",
            added_by=self.user,
        )
        image = AuslagerorteImage.objects.create(
            auslagerort=self.place,
            image=image_upload("hut.png"),
        )

        response = self.client.get(
            self.contract_url("place-detail", self.place),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"places"})
        self.assertEqual(len(response.json()["places"]), 1)
        place = response.json()["places"][0]
        self.assertEqual(set(place), DETAIL_FIELDS)
        self.assertEqual(place["contact"], "Ada +43 123")
        self.assertEqual(place["parking_coordinates"], "48.51, 15.01")
        self.assertEqual(place["images"], [image.image.url])
        self.assertEqual(place["notes"], [{
            "id": note.id,
            "text": "Wasser abdrehen",
            "author": "places-user",
            "date": note.date_added.isoformat(),
            "day": note.date_added.strftime("%d.%m."),
        }])

    def test_form_and_image_contracts_return_only_their_required_initial_values(self):
        create_response = self.client.get(self.contract_url("place-create"))
        update_response = self.client.get(
            self.contract_url("place-update", self.place),
        )
        images_response = self.client.get(
            self.contract_url("place-images", self.place),
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json(), {"places": []})
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(len(update_response.json()["places"]), 1)
        update_place = update_response.json()["places"][0]
        self.assertEqual(set(update_place), FORM_FIELDS)
        self.assertEqual(update_place["name"], "Ada Hütte")
        self.assertEqual(update_place["street"], "Waldweg 4")
        self.assertEqual(update_place["description"], "Lagerplatz am Wald")
        self.assertNotIn("contact", update_place)
        self.assertNotIn("images", update_place)
        self.assertNotIn("notes", update_place)
        self.assertEqual(images_response.status_code, 200)
        self.assertEqual(len(images_response.json()["places"]), 1)
        self.assertEqual(
            set(images_response.json()["places"][0]),
            REFERENCE_FIELDS,
        )
        self.assertEqual(
            images_response.json()["places"][0],
            {"id": self.place.id, "name": "Ada Hütte"},
        )

    def test_contracts_require_authentication_and_reject_missing_places(self):
        missing_urls = [
            self.contract_url(key) + "?id=999999"
            for key in ("place-detail", "place-update", "place-images")
        ]
        malformed_urls = [
            self.contract_url(key) + "?id=not-a-number"
            for key in ("place-detail", "place-update", "place-images")
        ]

        for url in missing_urls + malformed_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

        self.client.logout()
        for key in (
            "places-list",
            "place-create",
            "place-detail",
            "place-update",
            "place-images",
        ):
            with self.subTest(contract=key):
                self.assertEqual(
                    self.client.get(self.contract_url(key)).status_code,
                    403,
                )

    def test_without_an_active_turnus_places_are_not_exposed(self):
        user_without_turnus = User.objects.create_user(
            username="places-no-active-turnus",
        )
        self.client.force_login(user_without_turnus)

        list_response = self.client.get(self.contract_url("places-list"))
        detail_response = self.client.get(
            self.contract_url("place-detail", self.place),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), {"places": []})
        self.assertEqual(detail_response.status_code, 404)

    def test_note_write_requires_csrf_and_is_current_in_the_detail_contract(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        target = f"/auslagerorte/{self.place.id}/"

        denied = csrf_client.post(
            reverse("form-submit-api"),
            {"_target": target, "notiz": "Ohne Token"},
        )
        token = csrf_client.get(reverse("bootstrap-api")).json()["csrf_token"]
        accepted = csrf_client.post(
            reverse("form-submit-api"),
            {"_target": target, "notiz": "Neue Ortsnotiz"},
            HTTP_X_CSRFTOKEN=token,
        )
        refreshed = csrf_client.get(
            self.contract_url("place-detail", self.place),
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(
            accepted.json(),
            {"ok": True, "redirect": target},
        )
        self.assertEqual(
            [note["text"] for note in refreshed.json()["places"][0]["notes"]],
            ["Neue Ortsnotiz"],
        )

    def test_create_update_and_searchable_name_refresh_use_existing_forms(self):
        target = f"/auslagerorte/{self.place.id}/update"

        invalid = self.client.post(
            reverse("form-submit-api"),
            {"_target": target, "name": ""},
        )
        with patch(
            "budo_app.auslagerorte_views.update_auslagerorte_coordinates",
            side_effect=lambda place: place,
        ):
            updated = self.client.post(
                reverse("form-submit-api"),
                {
                    "_target": target,
                    "name": "Neue Ada Hütte",
                    "strasse": "Waldweg 4",
                    "ort": "Sallingstadt",
                    "bundesland": "Niederösterreich",
                    "postleitzahl": "3931",
                    "land": "Österreich",
                    "maps_link": "https://maps.example.test/ada",
                    "beschreibung": "Lagerplatz am Wald",
                    "maps_link_parkspot": "https://maps.example.test/parking",
                },
            )
            created = self.client.post(
                reverse("form-submit-api"),
                {
                    "_target": "/auslagerorte/create",
                    "name": "Neue Waldhütte",
                    "land": "Österreich",
                },
            )

        refreshed = self.client.get(
            self.contract_url("place-update", self.place),
        )
        bootstrap = self.client.get(reverse("bootstrap-api"))
        created_place = Auslagerorte.objects.get(name="Neue Waldhütte")

        self.assertEqual(invalid.status_code, 422, invalid.json())
        self.assertFalse(invalid.json()["ok"])
        self.assertTrue(invalid.json()["errors"])
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json(),
            {
                "ok": True,
                "redirect": f"/auslagerorte/{self.place.id}/",
            },
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(
            created.json(),
            {
                "ok": True,
                "redirect": f"/auslagerorte/{created_place.id}/",
            },
        )
        self.assertEqual(
            refreshed.json()["places"][0]["name"],
            "Neue Ada Hütte",
        )
        self.assertIn(
            {"id": self.place.id, "name": "Neue Ada Hütte"},
            bootstrap.json()["search_index"]["places"],
        )
        self.assertIn(
            {"id": created_place.id, "name": "Neue Waldhütte"},
            bootstrap.json()["search_index"]["places"],
        )

    def test_multipart_image_write_redirects_to_storage_backed_detail_images(self):
        target = f"/auslagerorte/{self.place.id}/upload-image/"

        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": target,
                "images": [
                    image_upload("one.png"),
                    image_upload("two.png"),
                ],
            },
        )
        refreshed = self.client.get(
            self.contract_url("place-detail", self.place),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "redirect": f"/auslagerorte/{self.place.id}/",
            },
        )
        self.assertEqual(self.place.images.count(), 2)
        self.assertEqual(len(refreshed.json()["places"][0]["images"]), 2)
        self.assertEqual(
            refreshed.json()["places"][0]["images"],
            [image.image.url for image in self.place.images.order_by("id")],
        )
