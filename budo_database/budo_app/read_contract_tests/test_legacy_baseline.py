from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import Turnus
from budo_app.read_contracts.measurement import (
    QueryBudgetAssertions,
    measure_http_get,
)

from .fixtures import ActiveTurnusFixtureFactory


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class LegacyAppDataBaselineTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="baseline-author",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_legacy_app_data(self):
        return measure_http_get(
            self.client,
            reverse("app-data-api"),
        )

    def test_small_and_realistic_legacy_response_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = self.measure_legacy_app_data()

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = self.measure_legacy_app_data()

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(small.response.json()["kids"]), 3)
        self.assertEqual(len(realistic.response.json()["kids"]), 48)
        self.assertGreater(realistic.response_bytes, small.response_bytes)
        self.assertGreaterEqual(small.sql_time_ms, 0)
        self.assertGreaterEqual(realistic.sql_time_ms, 0)

        # Characterization guardrails, intentionally expressed as ceilings.
        self.assertQueryCountAtMost(realistic, 100)
        self.assertQueryGrowthAtMost(small, realistic, 40)
