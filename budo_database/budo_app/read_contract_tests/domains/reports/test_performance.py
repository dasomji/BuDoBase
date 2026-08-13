from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import Kinder, SpezialFamilien, Turnus
from budo_app.read_contract_tests.fixtures import ActiveTurnusFixtureFactory
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
class ReportContractPerformanceTests(QueryBudgetAssertions, TestCase):
    contract_keys = (
        "birthdays",
        "families",
        "kid-count",
        "murder-game",
        "serial-letter",
        "special-families",
    )

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="reports-performance")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)
        self.special_family = SpezialFamilien.objects.create(
            name="Performance-Haus",
            turnus=self.turnus,
        )

    def grow_to(self, *, kids, focuses, team, places):
        self.fixtures.grow_to(
            kids=kids,
            focuses=focuses,
            team=team,
            places=places,
        )
        Kinder.objects.filter(turnus=self.turnus).update(
            budo_family="S",
            spezial_familien=self.special_family,
            sozialversicherungsnr="1234 020712",
        )

    def measure_contracts(self):
        return {
            key: measure_http_get(
                self.client,
                reverse("route-data-api", kwargs={"contract_key": key}),
            )
            for key in self.contract_keys
        }

    def test_query_growth_is_bounded_and_payloads_beat_the_legacy_baseline(self):
        self.grow_to(kids=3, focuses=2, team=2, places=1)
        small = self.measure_contracts()

        self.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = self.measure_contracts()

        for key in self.contract_keys:
            with self.subTest(contract=key):
                self.assertEqual(small[key].status_code, 200)
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 6)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 1)
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
