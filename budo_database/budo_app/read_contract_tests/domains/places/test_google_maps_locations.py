from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from budo_app import location_services
from budo_app.models import Auslagerorte, Turnus


class GoogleMapsGatewayStub:
    def __init__(self, *, expansions=None, addresses=None):
        self.expansions = expansions or {}
        self.addresses = addresses or {}
        self.expanded_links = []
        self.geocoded_coordinates = []

    def expand_short_link(self, url):
        self.expanded_links.append(url)
        return self.expansions.get(url)

    def reverse_geocode(self, latitude, longitude):
        coordinates = (latitude, longitude)
        self.geocoded_coordinates.append(coordinates)
        return self.addresses.get(coordinates)


class RejectingGoogleMapsGatewayStub:
    def expand_short_link(self, url):
        raise AssertionError(f"unchanged link was expanded: {url}")

    def reverse_geocode(self, latitude, longitude):
        raise AssertionError(
            f"unchanged coordinates were reverse-geocoded: {latitude},{longitude}"
        )


class GoogleMapsUrlParserTests(TestCase):
    def test_real_world_google_maps_url_fixtures(self):
        fixtures = {
            "place data uses the last coordinate pair": (
                "https://www.google.com/maps/place/Test/"
                "data=!3d47.1!4d15.2!8m2!3d48.2081743!4d16.3738189",
                (48.2081743, 16.3738189),
            ),
            "map viewport": (
                "https://www.google.at/maps/@48.305907,15.880139,15z",
                (48.305907, 15.880139),
            ),
            "query coordinates including zero": (
                "https://maps.google.com/?q=0,-78.4678",
                (0.0, -78.4678),
            ),
            "search path coordinates from a dropped pin": (
                "https://www.google.com/maps/search/47.81071,+13.05501",
                (47.81071, 13.05501),
            ),
            "expanded dropped-pin short link": (
                "https://www.google.com/maps/place/47%C2%B048'38.6%22N+"
                "13%C2%B003'18.0%22E/@47.81072,13.055,17z/"
                "data=!3m1!4b1!4m4!3m3!8m2!3d47.81071!4d13.05501",
                (47.81071, 13.05501),
            ),
            "consent redirect": (
                "https://consent.google.com/m?continue=https://www.google.com/maps",
                None,
            ),
            "place id without coordinates": (
                "https://www.google.com/maps/search/?api=1&query_place_id=ChIJ123",
                None,
            ),
            "latitude outside valid range": (
                "https://www.google.com/maps/@91,15,12z",
                None,
            ),
            "longitude outside valid range": (
                "https://www.google.com/maps/?q=48,181",
                None,
            ),
            "non-Google host": (
                "https://example.test/maps/@48.2081743,16.3738189",
                None,
            ),
        }

        for label, (url, expected) in fixtures.items():
            with self.subTest(label=label):
                self.assertEqual(
                    location_services.parse_google_maps_coordinates(url),
                    expected,
                )


class GoogleMapsPlaceWriteContractTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(
            turnus_nr=177,
            turnus_beginn=date(2026, 7, 1),
        )
        user = User.objects.create_user(
            username="google-maps-place-writer",
            password="secret",
        )
        user.profil.turnus = turnus
        user.profil.save()
        self.client.force_login(user)

    def submit(self, target, **values):
        payload = {
            "_target": target,
            "name": "Waldlichtung",
            "strasse": "",
            "ort": "",
            "bundesland": "",
            "postleitzahl": "",
            "land": "",
            "maps_link": "",
            "beschreibung": "",
            "maps_link_parkspot": "",
        }
        payload.update(values)
        return self.client.post(reverse("form-submit-api"), payload)

    def contract(self, key, place):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return self.client.get(f"{url}?id={place.id}").json()["places"][0]

    def queued_messages(self):
        return self.client.get(reverse("bootstrap-api")).json()["messages"]

    def test_create_expands_short_link_and_enriches_only_main_location(self):
        short_link = "https://maps.app.goo.gl/dropped-pin"
        expanded_link = (
            "https://www.google.com/maps/place/Wald/"
            "data=!3d48.2081743!4d16.3738189"
        )
        gateway = GoogleMapsGatewayStub(
            expansions={short_link: expanded_link},
            addresses={
                (48.2081743, 16.3738189): {
                    "street": "Waldweg 7",
                    "city": "Wien",
                    "state": "Wien",
                    "postal_code": "1010",
                    "country": "Österreich",
                },
            },
        )

        with patch.object(
            location_services,
            "google_maps_gateway",
            gateway,
            create=True,
        ):
            response = self.submit(
                "/auslagerorte/create",
                maps_link=short_link,
                maps_link_parkspot="https://www.google.com/maps/?q=0,16.4",
            )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        detail = self.contract("place-detail", place)

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.koordinaten, "48.2081743,16.3738189")
        self.assertEqual(place.koordinaten_parkspot, "0.0,16.4")
        self.assertEqual(
            (
                detail["street"],
                detail["city"],
                detail["state"],
                detail["postal_code"],
                detail["country"],
                detail["coordinates"],
                detail["parking_coordinates"],
            ),
            (
                "Waldweg 7",
                "Wien",
                "Wien",
                "1010",
                "Österreich",
                "48.2081743,16.3738189",
                "0.0,16.4",
            ),
        )
        self.assertEqual(gateway.expanded_links, [short_link])
        self.assertEqual(
            gateway.geocoded_coordinates,
            [(48.2081743, 16.3738189)],
        )

    def test_create_never_overwrites_user_address_values(self):
        gateway = GoogleMapsGatewayStub(
            addresses={
                (48.3, 15.8): {
                    "street": "Googlestraße 9",
                    "city": "Google-Stadt",
                    "state": "Google-Land",
                    "postal_code": "9999",
                    "country": "Google-Land",
                },
            },
        )

        with patch.object(
            location_services,
            "google_maps_gateway",
            gateway,
            create=True,
        ):
            self.submit(
                "/auslagerorte/create",
                maps_link="https://www.google.com/maps/@48.3,15.8,17z",
                strasse="Forstweg ohne Hausnummer",
                ort="Unser Ortsname",
                land="Österreich",
            )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        self.assertEqual(place.strasse, "Forstweg ohne Hausnummer")
        self.assertEqual(place.ort, "Unser Ortsname")
        self.assertEqual(place.land, "Österreich")
        self.assertEqual(place.bundesland, "Google-Land")
        self.assertEqual(place.postleitzahl, "9999")

    def test_create_accepts_long_google_maps_parkspot_link(self):
        parking_link = (
            "https://www.google.com/maps/?q=48.2,15.2&entry=ttu&padding="
            + "x" * 220
        )

        response = self.submit(
            "/auslagerorte/create",
            maps_link_parkspot=parking_link,
        )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        self.assertGreater(len(parking_link), 200)
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.maps_link_parkspot, parking_link)
        self.assertEqual(place.koordinaten_parkspot, "48.2,15.2")

    def test_update_accepts_long_google_maps_main_link(self):
        place = Auslagerorte.objects.create(name="Waldlichtung")
        main_link = (
            "https://www.google.com/maps/@48.3,15.8,17z?entry=ttu&padding="
            + "x" * 220
        )

        response = self.submit(
            f"/auslagerorte/{place.id}/update",
            maps_link=main_link,
        )

        place.refresh_from_db()
        self.assertGreater(len(main_link), 200)
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.maps_link, main_link)
        self.assertEqual(place.koordinaten, "48.3,15.8")

    def test_changed_invalid_links_clear_stale_coordinates_and_warn_user(self):
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            maps_link="https://www.google.com/maps/@48.1,15.1,17z",
            koordinaten="48.1,15.1",
            maps_link_parkspot="https://www.google.com/maps/?q=48.2,15.2",
            koordinaten_parkspot="48.2,15.2",
        )
        gateway = GoogleMapsGatewayStub()

        with patch.object(
            location_services,
            "google_maps_gateway",
            gateway,
            create=True,
        ):
            response = self.submit(
                f"/auslagerorte/{place.id}/update",
                maps_link="https://www.google.com/maps/place/NoCoordinates",
                maps_link_parkspot=(
                    "https://www.google.com/maps/search/PlaceIdOnly"
                    "?query_place_id=ChIJ123"
                ),
            )

        place.refresh_from_db()
        warnings = [
            message["text"]
            for message in self.queued_messages()
            if message["tags"] == "warning"
        ]

        self.assertEqual(response.status_code, 200, response.json())
        self.assertIsNone(place.koordinaten)
        self.assertIsNone(place.koordinaten_parkspot)
        self.assertTrue(
            any("Koordinaten" in warning for warning in warnings),
            warnings,
        )
        self.assertTrue(
            any("Parkspot" in warning for warning in warnings),
            warnings,
        )

    def test_unchanged_links_skip_all_google_gateway_work(self):
        main_link = "https://www.google.com/maps/@48.1,15.1,17z"
        parking_link = "https://www.google.com/maps/?q=48.2,15.2"
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            maps_link=main_link,
            koordinaten="48.1,15.1",
            maps_link_parkspot=parking_link,
            koordinaten_parkspot="48.2,15.2",
        )

        with patch.object(
            location_services,
            "google_maps_gateway",
            RejectingGoogleMapsGatewayStub(),
            create=True,
        ):
            response = self.submit(
                f"/auslagerorte/{place.id}/update",
                maps_link=main_link,
                maps_link_parkspot=parking_link,
                beschreibung="Neue Wegbeschreibung",
            )

        place.refresh_from_db()
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.beschreibung, "Neue Wegbeschreibung")
        self.assertEqual(place.koordinaten, "48.1,15.1")
        self.assertEqual(place.koordinaten_parkspot, "48.2,15.2")


class BackfillGoogleMapsLocationsCommandTests(TestCase):
    def test_backfills_only_missing_coordinates_and_optionally_enriches_address(self):
        missing = Auslagerorte.objects.create(
            name="Alter Waldplatz",
            maps_link="https://maps.app.goo.gl/old-place",
            maps_link_parkspot="https://www.google.com/maps/?q=48.41,15.91",
            land="",
        )
        complete = Auslagerorte.objects.create(
            name="Bereits vollständig",
            maps_link="https://maps.app.goo.gl/already-complete",
            koordinaten="48.5,15.5",
            strasse="Bestehender Weg 1",
        )
        gateway = GoogleMapsGatewayStub(
            expansions={
                missing.maps_link: "https://www.google.com/maps/@48.4,15.9,17z",
            },
            addresses={
                (48.4, 15.9): {
                    "street": "Nachgetragener Waldweg",
                    "city": "Zwettl",
                    "state": "Niederösterreich",
                    "postal_code": "3910",
                    "country": "Österreich",
                },
            },
        )
        output = StringIO()

        with patch.object(
            location_services,
            "google_maps_gateway",
            gateway,
            create=True,
        ):
            call_command(
                "backfill_auslagerorte_coordinates",
                enrich_addresses=True,
                stdout=output,
            )

        missing.refresh_from_db()
        complete.refresh_from_db()
        self.assertEqual(missing.koordinaten, "48.4,15.9")
        self.assertEqual(missing.koordinaten_parkspot, "48.41,15.91")
        self.assertEqual(missing.strasse, "Nachgetragener Waldweg")
        self.assertEqual(missing.ort, "Zwettl")
        self.assertEqual(complete.koordinaten, "48.5,15.5")
        self.assertEqual(complete.strasse, "Bestehender Weg 1")
        self.assertNotIn(complete.maps_link, gateway.expanded_links)
        self.assertIn("Alter Waldplatz", output.getvalue())
