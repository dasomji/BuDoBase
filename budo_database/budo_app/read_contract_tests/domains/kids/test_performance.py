from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.models import ErsteHilfeEintrag, Geld, Kinder, Notizen, Turnus
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
class KidsContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kids-performance-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def contract_url(self, key, **params):
        base = reverse("route-data-api", kwargs={"contract_key": key})
        if not params:
            return base
        query = "&".join(f"{name}={value}" for name, value in params.items())
        return f"{base}?{query}"

    def test_directory_queries_stay_bounded_and_payload_beats_the_legacy_baseline(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = measure_http_get(
            self.client,
            self.contract_url("kids-directory"),
        )

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(
            self.client,
            self.contract_url("kids-directory"),
        )

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(realistic.response.json()["kids"]), 48)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
        self.assertQueryCountAtMost(realistic, 10)
        self.assertQueryGrowthAtMost(small, realistic, 1)

    def test_detail_queries_stay_bounded_as_kinder_and_histories_grow(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        kid = Kinder.objects.filter(turnus=self.turnus).order_by("id").first()
        small = measure_http_get(
            self.client,
            self.contract_url("kid-detail", id=kid.id),
        )

        for index in range(40):
            Notizen.objects.create(
                kinder=kid,
                notiz=f"Zusätzliche Notiz {index}",
                added_by=self.user,
            )
            ErsteHilfeEintrag.objects.create(
                kinder=kid,
                beschreibung=f"Zusätzlicher EH-Eintrag {index}",
                added_by=self.user,
            )
            Geld.objects.create(
                kinder=kid,
                amount=-1,
                added_by=self.user,
            )
        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)

        realistic = measure_http_get(
            self.client,
            self.contract_url("kid-detail", id=kid.id),
        )

        payload = realistic.response.json()["kids"][0]
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(payload["notes"]), 42)
        self.assertEqual(len(payload["first_aid_entries"]), 42)
        self.assertEqual(len(payload["transactions"]), 42)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
        self.assertQueryCountAtMost(realistic, 12)
        self.assertQueryGrowthAtMost(small, realistic, 1)
