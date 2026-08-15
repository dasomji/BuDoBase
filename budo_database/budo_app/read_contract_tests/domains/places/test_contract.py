from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
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


DETAIL_FIELDS = {
    "id",
    "name",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "coordinates",
    "driving_minutes",
    "walking_minutes",
    "maps_link",
    "description",
    "contact",
    "parking_link",
    "parking_coordinates",
    "images",
    "gallery_images",
    "notes",
    "tags",
    "marker_icon",
}

LIST_FIELDS = DETAIL_FIELDS

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
    "contact",
    "parking_link",
    "tags",
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
        approve_and_select_turnus(self.user.profil.user, self.turnus)
        self.user.profil.rufname = "Pia"
        self.user.profil.save()
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.place = Auslagerorte.objects.create(
            name="Ada Hütte",
            strasse="Waldweg 4",
            ort="Sallingstadt",
            bundesland="Niederösterreich",
            postleitzahl="3931",
            land="Österreich",
            koordinaten="48.5, 15.0",
            driving_minutes=14,
            walking_minutes=51,
            maps_link="https://maps.example.test/ada",
            maps_link_parkspot="https://maps.example.test/parking",
            koordinaten_parkspot="48.51, 15.01",
            beschreibung="Lagerplatz am Wald",
            kontakt="Ada +43 123",
        )

    def contract_url(self, key, place=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={place.id}" if place else url

    def test_list_returns_the_ordered_complete_map_sidebar_projection(self):
        Auslagerorte.objects.create(name="Zeltplatz")

        response = self.client.get(self.contract_url("places-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"places", "available_tags", "tag_catalog"})
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
                "street": "Waldweg 4",
                "city": "Sallingstadt",
                "state": "Niederösterreich",
                "postal_code": "3931",
                "country": "Österreich",
                "coordinates": "48.5, 15.0",
                "driving_minutes": 14,
                "walking_minutes": 51,
                "maps_link": "https://maps.example.test/ada",
                "parking_link": "https://maps.example.test/parking",
                "parking_coordinates": "48.51, 15.01",
                "description": "Lagerplatz am Wald",
                "contact": "Ada +43 123",
                "images": [],
                "gallery_images": [],
                "notes": [],
                "tags": [],
                "marker_icon": "map-pin",
            },
        )
        self.assertEqual(response.json()["available_tags"], [])
        self.assertEqual(response.json()["tag_catalog"], [])

    def test_list_preserves_empty_behavior(self):
        Auslagerorte.objects.all().delete()

        response = self.client.get(self.contract_url("places-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"places": [], "available_tags": [], "tag_catalog": []})

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
        self.assertEqual(place["driving_minutes"], 14)
        self.assertEqual(place["walking_minutes"], 51)
        self.assertEqual(place["images"], [image.image.url])
        self.assertEqual(place["gallery_images"], [{
            "id": image.id,
            "url": image.image.url,
            "alt": "Bild von Ada Hütte",
            "comment_text": None,
        }])
        self.assertEqual(place["notes"], [{
            "id": note.id,
            "text": "Wasser abdrehen",
            "author": "Pia",
            "date": note.date_added.isoformat(),
            "day": note.date_added.strftime("%d.%m."),
            "photos": [],
        }])
        self.assertEqual(place["tags"], [])

    def test_form_and_image_contracts_return_only_their_required_initial_values(self):
        create_response = self.client.get(self.contract_url("place-create"))
        update_response = self.client.get(
            self.contract_url("place-update", self.place),
        )
        images_response = self.client.get(
            self.contract_url("place-images", self.place),
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(
            create_response.json(),
            {"places": [], "available_tags": [], "tag_catalog": []},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(len(update_response.json()["places"]), 1)
        update_place = update_response.json()["places"][0]
        self.assertEqual(set(update_place), FORM_FIELDS)
        self.assertEqual(update_place["name"], "Ada Hütte")
        self.assertEqual(update_place["street"], "Waldweg 4")
        self.assertEqual(update_place["contact"], "Ada +43 123")
        self.assertEqual(update_place["description"], "Lagerplatz am Wald")
        self.assertEqual(update_place["tags"], [])
        self.assertEqual(update_response.json()["available_tags"], [])
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
        self.assertEqual(
            list_response.json(),
            {"places": [], "available_tags": [], "tag_catalog": []},
        )
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

    def test_comment_images_are_tied_to_the_note_but_not_the_place_carousel(self):
        target = f"/auslagerorte/{self.place.id}/"

        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": target,
                "notiz": "Beschädigte Feuerstelle",
                "images": [image_upload("damage.png")],
            },
        )
        refreshed = self.client.get(
            self.contract_url("place-detail", self.place),
        ).json()["places"][0]

        self.assertEqual(response.status_code, 200, response.json())
        note = AuslagerorteNotizen.objects.get(notiz="Beschädigte Feuerstelle")
        image = self.place.images.get()
        self.assertEqual(image.notiz, note)
        self.assertEqual(refreshed["images"], [])
        expected_photo = {
            "id": image.id,
            "url": image.image.url,
            "alt": "Kommentarbild zu Ada Hütte",
        }
        self.assertEqual(refreshed["notes"][0]["photos"], [expected_photo])
        self.assertEqual(refreshed["gallery_images"], [{
            **expected_photo,
            "comment_text": "Beschädigte Feuerstelle",
        }])

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
                    "kontakt": "Ada aktualisiert\n+43 456",
                    "maps_link_parkspot": "https://maps.example.test/parking",
                },
            )
            created = self.client.post(
                reverse("form-submit-api"),
                {
                    "_target": "/auslagerorte/create",
                    "name": "Neue Waldhütte",
                    "land": "Österreich",
                    "kontakt": "Förster Max\n+43 789",
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
        self.assertEqual(
            refreshed.json()["places"][0]["contact"],
            "Ada aktualisiert\n+43 456",
        )
        self.assertEqual(created_place.kontakt, "Förster Max\n+43 789")
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
