from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import bulk_create_first_aid_entries_for_test
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
class DashboardContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="dashboard-performance")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def contract_url(self):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "dashboard"},
        )

    def test_initial_query_growth_is_bounded_and_payload_beats_legacy(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = measure_http_get(self.client, self.contract_url())

        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = measure_http_get(self.client, self.contract_url())

        self.assertEqual(small.status_code, 200)
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(realistic.response.json()["kids"]), 48)
        self.assertEqual(
            len(realistic.response.json()["activity"]["notes"]["items"]),
            20,
        )
        self.assertEqual(
            len(realistic.response.json()["activity"]["first_aid"]["items"]),
            20,
        )
        self.assertEqual(
            len(realistic.response.json()["activity"]["transactions"]["items"]),
            20,
        )
        self.assertQueryCountAtMost(realistic, 13)
        self.assertQueryGrowthAtMost(small, realistic, 1)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )

    def test_initial_activity_payload_stays_bounded_as_history_grows(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        kid = Kinder.objects.filter(turnus=self.turnus).first()
        Notizen.objects.bulk_create([
            Notizen(
                kinder=kid,
                notiz=f"Bereits vorhandene Notiz {index}",
                added_by=self.user,
            )
            for index in range(25)
        ])
        bulk_create_first_aid_entries_for_test([
            ErsteHilfeEintrag(
                kinder=kid,
                beschreibung=f"Bestehender EH-Eintrag {index}",
                added_by=self.user,
            )
            for index in range(25)
        ])
        Geld.objects.bulk_create([
            Geld(kinder=kid, amount=index, added_by=self.user)
            for index in range(25)
        ])
        before = measure_http_get(self.client, self.contract_url())
        Notizen.objects.bulk_create([
            Notizen(
                kinder=kid,
                notiz=f"Historische Notiz {index}",
                added_by=self.user,
            )
            for index in range(200)
        ])
        bulk_create_first_aid_entries_for_test([
            ErsteHilfeEintrag(
                kinder=kid,
                beschreibung=f"Historischer EH-Eintrag {index}",
                added_by=self.user,
            )
            for index in range(200)
        ])
        Geld.objects.bulk_create([
            Geld(kinder=kid, amount=index, added_by=self.user)
            for index in range(200)
        ])

        after = measure_http_get(self.client, self.contract_url())

        self.assertQueryCountAtMost(after, 13)
        self.assertQueryGrowthAtMost(before, after, 0)
        self.assertEqual(len(after.response.json()["activity"]["notes"]["items"]), 20)
        self.assertEqual(
            len(after.response.json()["activity"]["first_aid"]["items"]),
            20,
        )
        self.assertEqual(
            len(after.response.json()["activity"]["transactions"]["items"]),
            20,
        )
        self.assertLess(after.response_bytes - before.response_bytes, 2_000)
