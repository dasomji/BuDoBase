from datetime import date
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from budo_app import google_maps_gateway, location_services
from budo_app.models import Auslagerorte, Turnus


class RouteDurationGatewayStub:
    def __init__(self, durations=None, *, error=None):
        self.durations = durations or {}
        self.error = error
        self.route_requests = []

    def expand_short_link(self, url):
        raise AssertionError(f"unexpected short-link expansion: {url}")

    def reverse_geocode(self, latitude, longitude):
        return None

    def route_duration_minutes(
        self,
        origin_coordinates,
        destination_coordinates,
        travel_mode,
    ):
        request = (origin_coordinates, destination_coordinates, travel_mode)
        self.route_requests.append(request)
        if self.error:
            raise self.error
        return self.durations.get(travel_mode)


class RejectingRouteDurationGatewayStub(RouteDurationGatewayStub):
    def route_duration_minutes(
        self,
        origin_coordinates,
        destination_coordinates,
        travel_mode,
    ):
        raise AssertionError(
            "unchanged coordinates requested a route: "
            f"{origin_coordinates} -> {destination_coordinates} ({travel_mode})"
        )


class TravelTimeStorageTests(TestCase):
    def test_travel_minutes_are_nullable_integer_fields(self):
        place = Auslagerorte.objects.create(name="Noch ohne Standort")

        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)
        self.assertEqual(
            Auslagerorte._meta.get_field("driving_minutes").get_internal_type(),
            "IntegerField",
        )
        self.assertEqual(
            Auslagerorte._meta.get_field("walking_minutes").get_internal_type(),
            "IntegerField",
        )

    def test_direct_coordinate_save_recomputes_both_travel_times(self):
        Auslagerorte.objects.create(name="BuDo", koordinaten="48.0,15.0")
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            koordinaten="48.1,15.1",
            driving_minutes=8,
            walking_minutes=25,
        )
        gateway = RouteDurationGatewayStub({"DRIVE": 12, "WALK": 47})

        place.koordinaten = "48.2,15.2"
        with patch.object(location_services, "google_maps_gateway", gateway):
            place.save(update_fields=["koordinaten"])

        place.refresh_from_db()
        self.assertEqual((place.driving_minutes, place.walking_minutes), (12, 47))
        self.assertEqual(
            gateway.route_requests,
            [
                ((48.0, 15.0), (48.2, 15.2), "DRIVE"),
                ((48.0, 15.0), (48.2, 15.2), "WALK"),
            ],
        )

    def test_direct_coordinate_clear_clears_both_travel_times(self):
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            koordinaten="48.1,15.1",
            driving_minutes=8,
            walking_minutes=25,
        )

        place.koordinaten = None
        place.save()

        place.refresh_from_db()
        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)

    def test_admin_save_uses_the_coordinate_travel_time_invariant(self):
        Auslagerorte.objects.create(name="BuDo", koordinaten="48.0,15.0")
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            koordinaten="48.1,15.1",
            driving_minutes=8,
            walking_minutes=25,
        )
        place.koordinaten = "48.2,15.2"
        gateway = RouteDurationGatewayStub({"DRIVE": 12, "WALK": 47})
        model_admin = admin.site._registry[Auslagerorte]

        with patch.object(location_services, "google_maps_gateway", gateway):
            model_admin.save_model(
                RequestFactory().post("/admin/budo_app/auslagerorte/"),
                place,
                form=None,
                change=True,
            )

        place.refresh_from_db()
        self.assertEqual((place.driving_minutes, place.walking_minutes), (12, 47))


class TravelTimeWriteContractTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(
            turnus_nr=179,
            turnus_beginn=date(2026, 7, 1),
        )
        user = User.objects.create_user(
            username="travel-time-place-writer",
            password="secret",
        )
        user.profil.turnus = turnus
        user.profil.save()
        self.client.force_login(user)
        self.budo = Auslagerorte.objects.create(
            name="BuDo",
            koordinaten="48.0,15.0",
        )

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

    def test_link_pipeline_stores_both_routes_when_main_coordinates_are_set(self):
        gateway = RouteDurationGatewayStub({"DRIVE": 12, "WALK": 47})

        with patch.object(location_services, "google_maps_gateway", gateway):
            response = self.submit(
                "/auslagerorte/create",
                maps_link="https://www.google.com/maps/@48.2,15.2,17z",
                maps_link_parkspot="https://www.google.com/maps/?q=48.3,15.3",
            )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.koordinaten, "48.2,15.2")
        self.assertEqual(place.driving_minutes, 12)
        self.assertEqual(place.walking_minutes, 47)
        self.assertEqual(
            gateway.route_requests,
            [
                ((48.0, 15.0), (48.2, 15.2), "DRIVE"),
                ((48.0, 15.0), (48.2, 15.2), "WALK"),
            ],
        )

    def test_unchanged_main_coordinates_and_parkspot_changes_skip_routes(self):
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            maps_link="https://www.google.com/maps/@48.2,15.2,17z",
            koordinaten="48.2,15.2",
            driving_minutes=12,
            walking_minutes=47,
        )

        with patch.object(
            location_services,
            "google_maps_gateway",
            RejectingRouteDurationGatewayStub(),
        ):
            response = self.submit(
                f"/auslagerorte/{place.id}/update",
                maps_link="https://www.google.com/maps/?q=48.2,15.2",
                maps_link_parkspot="https://www.google.com/maps/?q=48.3,15.3",
                beschreibung="Neue Beschreibung",
            )

        place.refresh_from_db()
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.driving_minutes, 12)
        self.assertEqual(place.walking_minutes, 47)

    def test_clearing_main_coordinates_clears_both_travel_times(self):
        place = Auslagerorte.objects.create(
            name="Waldlichtung",
            maps_link="https://www.google.com/maps/@48.2,15.2,17z",
            koordinaten="48.2,15.2",
            driving_minutes=12,
            walking_minutes=47,
        )

        with patch.object(
            location_services,
            "google_maps_gateway",
            RejectingRouteDurationGatewayStub(),
        ):
            response = self.submit(
                f"/auslagerorte/{place.id}/update",
                maps_link="",
            )

        place.refresh_from_db()
        self.assertEqual(response.status_code, 200, response.json())
        self.assertIsNone(place.koordinaten)
        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)

    def test_route_failure_saves_place_without_times_and_warns(self):
        gateway = RouteDurationGatewayStub(error=RuntimeError("routes offline"))

        with self.assertLogs("budo_app.location_services", level="WARNING") as logs:
            with patch.object(location_services, "google_maps_gateway", gateway):
                response = self.submit(
                    "/auslagerorte/create",
                    maps_link="https://www.google.com/maps/@48.2,15.2,17z",
                )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        warnings = [
            message["text"]
            for message in self.client.get(reverse("bootstrap-api")).json()["messages"]
            if message["tags"] == "warning"
        ]
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(place.koordinaten, "48.2,15.2")
        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)
        self.assertTrue(warnings)
        self.assertTrue(any("routes offline" in entry for entry in logs.output))

    def test_missing_budo_coordinates_skip_routes_and_log_notice(self):
        self.budo.koordinaten = None
        self.budo.save(update_fields=["koordinaten"])
        gateway = RejectingRouteDurationGatewayStub()

        with self.assertLogs("budo_app.location_services", level="INFO") as logs:
            with patch.object(location_services, "google_maps_gateway", gateway):
                response = self.submit(
                    "/auslagerorte/create",
                    maps_link="https://www.google.com/maps/@48.2,15.2,17z",
                )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)
        self.assertTrue(any("BuDo" in entry for entry in logs.output), logs.output)

    def test_missing_budo_place_skips_routes_and_log_notice(self):
        self.budo.delete()
        gateway = RejectingRouteDurationGatewayStub()

        with self.assertLogs("budo_app.location_services", level="INFO") as logs:
            with patch.object(location_services, "google_maps_gateway", gateway):
                response = self.submit(
                    "/auslagerorte/create",
                    maps_link="https://www.google.com/maps/@48.2,15.2,17z",
                )

        place = Auslagerorte.objects.get(name="Waldlichtung")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertIsNone(place.driving_minutes)
        self.assertIsNone(place.walking_minutes)
        self.assertTrue(any("BuDo" in entry for entry in logs.output), logs.output)


class TravelTimeReadContractTests(TestCase):
    def setUp(self):
        turnus = Turnus.objects.create(
            turnus_nr=179,
            turnus_beginn=date(2026, 7, 1),
        )
        user = User.objects.create_user(username="travel-time-reader")
        user.profil.turnus = turnus
        user.profil.save()
        self.client.force_login(user)
        self.place = Auslagerorte.objects.create(
            name="Waldlichtung",
            koordinaten="48.2,15.2",
            driving_minutes=12,
            walking_minutes=47,
        )

    def contract(self, key):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        suffix = f"?id={self.place.id}" if key == "place-detail" else ""
        return self.client.get(f"{url}{suffix}").json()["places"]

    def test_list_and_detail_expose_both_travel_minutes(self):
        list_place = next(
            place for place in self.contract("places-list")
            if place["id"] == self.place.id
        )
        detail_place = self.contract("place-detail")[0]

        self.assertEqual(list_place["driving_minutes"], 12)
        self.assertEqual(list_place["walking_minutes"], 47)
        self.assertEqual(detail_place["driving_minutes"], 12)
        self.assertEqual(detail_place["walking_minutes"], 47)


class BackfillTravelTimesCommandTests(TestCase):
    def test_backfills_missing_times_and_skips_complete_or_coordinate_less_places(self):
        Auslagerorte.objects.create(
            name="BuDo",
            koordinaten="48.0,15.0",
            driving_minutes=0,
            walking_minutes=0,
        )
        missing = Auslagerorte.objects.create(
            name="Alter Waldplatz",
            koordinaten="48.4,15.9",
        )
        complete = Auslagerorte.objects.create(
            name="Bereits vollständig",
            koordinaten="48.5,15.5",
            driving_minutes=9,
            walking_minutes=31,
        )
        Auslagerorte.objects.create(name="Ohne Koordinaten")
        gateway = RouteDurationGatewayStub({"DRIVE": 18, "WALK": 64})
        output = StringIO()

        with patch.object(location_services, "google_maps_gateway", gateway):
            call_command("backfill_auslagerorte_travel_times", stdout=output)

        missing.refresh_from_db()
        complete.refresh_from_db()
        self.assertEqual(
            (missing.driving_minutes, missing.walking_minutes),
            (18, 64),
        )
        self.assertEqual(
            (complete.driving_minutes, complete.walking_minutes),
            (9, 31),
        )
        self.assertEqual(
            gateway.route_requests,
            [
                ((48.0, 15.0), (48.4, 15.9), "DRIVE"),
                ((48.0, 15.0), (48.4, 15.9), "WALK"),
            ],
        )
        self.assertIn("Alter Waldplatz", output.getvalue())


@override_settings(GOOGLE_MAPS_API_KEY="routes-test-key")
class GoogleRoutesGatewayTests(TestCase):
    @patch("budo_app.google_maps_gateway.requests.post")
    def test_route_duration_returns_whole_minutes(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"routes": [{"duration": "780s"}]}
        post.return_value = response

        duration = google_maps_gateway.route_duration_minutes(
            (48.0, 15.0),
            (48.2, 15.2),
            "WALK",
        )

        self.assertEqual(duration, 13)

    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_route_duration_without_api_key_fails_softly(self):
        with self.assertLogs("budo_app.google_maps_gateway", level="INFO"):
            duration = google_maps_gateway.route_duration_minutes(
                (48.0, 15.0),
                (48.2, 15.2),
                "DRIVE",
            )

        self.assertIsNone(duration)
