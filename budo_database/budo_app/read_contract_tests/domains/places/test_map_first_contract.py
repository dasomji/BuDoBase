from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Tag,
    Turnus,
)
from budo_app.read_contract_tests.fixtures import image_upload


TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class MapFirstPlacesContractTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="mia", password="secret")
        self.user.profil.turnus = turnus
        self.user.profil.save()
        create_membership(user=self.user, turnus=turnus)
        select_turnus(self.user, turnus)
        self.client.force_login(self.user)

    def test_list_carries_everything_the_map_sidebar_needs_without_a_detail_fetch(self):
        place = Auslagerorte.objects.create(
            name="Waldwiese",
            strasse="Waldweg 4",
            ort="Sallingstadt",
            bundesland="Niederösterreich",
            postleitzahl="3931",
            land="Österreich",
            koordinaten="48.50000, 15.00000",
            driving_minutes=14,
            walking_minutes=51,
            maps_link="https://maps.example.test/waldwiese",
            beschreibung="Schattiger Lagerplatz am Waldrand.",
            kontakt="Försterin Ada",
            maps_link_parkspot="https://maps.example.test/parkplatz",
            koordinaten_parkspot="48.51000, 15.01000",
        )
        place.tags.add(Tag.objects.create(name="Wanderung"))
        image = AuslagerorteImage.objects.create(
            auslagerort=place,
            image=image_upload("wald.png"),
        )
        note = AuslagerorteNotizen.objects.create(
            auslagerort=place,
            notiz="Das Gatter bitte schließen.",
            added_by=self.user,
        )
        note_image = AuslagerorteImage.objects.create(
            auslagerort=place,
            notiz=note,
            image=image_upload("gatter.png"),
        )

        response = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "places-list"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_tags"], ["Wanderung"])
        self.assertEqual(response.json()["places"], [{
            "id": place.id,
            "name": "Waldwiese",
            "street": "Waldweg 4",
            "city": "Sallingstadt",
            "state": "Niederösterreich",
            "postal_code": "3931",
            "country": "Österreich",
            "coordinates": "48.50000, 15.00000",
            "driving_minutes": 14,
            "walking_minutes": 51,
            "maps_link": "https://maps.example.test/waldwiese",
            "description": "Schattiger Lagerplatz am Waldrand.",
            "contact": "Försterin Ada",
            "parking_link": "https://maps.example.test/parkplatz",
            "parking_coordinates": "48.51000, 15.01000",
            "images": [image.image.url],
            "gallery_images": [{
                "id": image.id,
                "url": image.image.url,
                "alt": "Bild von Waldwiese",
                "comment_text": None,
            }, {
                "id": note_image.id,
                "url": note_image.image.url,
                "alt": "Kommentarbild zu Waldwiese",
                "comment_text": "Das Gatter bitte schließen.",
            }],
            "notes": [{
                "id": note.id,
                "text": "Das Gatter bitte schließen.",
                "author": "mia",
                "date": note.date_added.isoformat(),
                "day": note.date_added.strftime("%d.%m."),
                "photos": [{
                    "id": note_image.id,
                    "url": note_image.image.url,
                    "alt": "Kommentarbild zu Waldwiese",
                }],
            }],
            "tags": ["Wanderung"],
            "marker_icon": "map-pin",
        }])
