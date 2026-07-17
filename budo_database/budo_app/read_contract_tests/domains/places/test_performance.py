from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Turnus,
)
from budo_app.read_contract_tests.fixtures import (
    ActiveTurnusFixtureFactory,
    image_upload,
)
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
)


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class PlacesContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="places-performance",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contract(self, key, place=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        if place:
            url = f"{url}?id={place.id}"
        return measure_http_get(self.client, url)

    def measurements(self, place):
        return {
            "places-list": self.measure_contract("places-list"),
            "place-create": self.measure_contract("place-create"),
            "place-detail": self.measure_contract("place-detail", place),
            "place-update": self.measure_contract("place-update", place),
            "place-images": self.measure_contract("place-images", place),
        }

    def test_query_growth_is_bounded_and_payloads_beat_the_legacy_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=3)
        place = Auslagerorte.objects.filter(
            name__startswith="Baseline Ort",
        ).order_by("id").first()
        small = self.measurements(place)

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=40)
        for index in range(1, 30):
            AuslagerorteNotizen.objects.create(
                auslagerort=place,
                notiz=f"Skalierende Ortsnotiz {index}",
                added_by=self.user,
            )
            AuslagerorteImage.objects.create(
                auslagerort=place,
                image=image_upload(f"scaled-place-{index}.png"),
            )
        realistic = self.measurements(place)

        for key in small:
            with self.subTest(contract=key):
                self.assertEqual(small[key].status_code, 200)
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 9)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 1)
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
