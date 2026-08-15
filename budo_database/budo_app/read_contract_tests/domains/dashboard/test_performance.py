from budo_app.test_membership_fixtures import approve_and_select_turnus
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import bulk_create_first_aid_entries_for_test
from budo_app.memberships import create_membership, select_turnus
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
        approve_and_select_turnus(self.user.profil.user, self.turnus)
        self.user.profil.save()
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def contract_url(self, key="dashboard"):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": key},
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
            set(realistic.response.json()["activity"]),
            {"notes", "first_aid"},
        )
        # Includes the bounded personal Happy-Cleaning station projection.
        # Includes BEGIN/COMMIT for the membership-lock lifetime.
        self.assertQueryCountAtMost(realistic, 17)
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

        # Includes the bounded personal Happy-Cleaning station projection.
        # Includes BEGIN/COMMIT for the membership-lock lifetime.
        self.assertQueryCountAtMost(after, 17)
        self.assertQueryGrowthAtMost(before, after, 0)
        self.assertEqual(len(after.response.json()["activity"]["notes"]["items"]), 20)
        self.assertEqual(
            len(after.response.json()["activity"]["first_aid"]["items"]),
            20,
        )
        self.assertEqual(
            set(after.response.json()["activity"]),
            {"notes", "first_aid"},
        )
        self.assertLess(after.response_bytes - before.response_bytes, 2_000)

    def test_pocket_money_activity_stays_bounded_as_history_grows(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        kid = Kinder.objects.filter(turnus=self.turnus).first()
        Geld.objects.bulk_create([
            Geld(kinder=kid, amount=index, added_by=self.user)
            for index in range(25)
        ])
        before = measure_http_get(self.client, self.contract_url("pocket-money"))
        Geld.objects.bulk_create([
            Geld(kinder=kid, amount=index, added_by=self.user)
            for index in range(200)
        ])

        after = measure_http_get(self.client, self.contract_url("pocket-money"))

        self.assertEqual(after.status_code, 200)
        self.assertQueryCountAtMost(after, 9)
        self.assertQueryGrowthAtMost(before, after, 0)
        self.assertEqual(
            len(after.response.json()["activity"]["transactions"]["items"]),
            20,
        )
        self.assertLess(after.response_bytes - before.response_bytes, 2_000)
