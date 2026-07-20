from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import MemoryPhotoStorage, use_photo_storage
from budo_app.first_aid_tests.fixtures import create_first_aid_entry_for_test
from budo_app.models import ErsteHilfeEintrag, Kinder, Turnus
from budo_app.read_contract_tests.first_aid_fixtures import add_first_aid_photo
from budo_app.read_contracts.measurement import (
    QueryBudgetAssertions,
    measure_http_get,
)


PHOTO_FIELDS = {"id", "url", "width", "height", "alt"}


class DashboardFirstAidPhotoContractTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="dashboard-photo-contract")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.kid = Kinder.objects.create(
            kid_index="T2-dashboard-photo",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
        )
        self.client.force_login(self.user)

    def contract_url(self, **params):
        base = reverse("route-data-api", kwargs={"contract_key": "dashboard"})
        if not params:
            return base
        from urllib.parse import urlencode

        return f"{base}?{urlencode(params)}"

    def create_entry(self, description):
        return create_first_aid_entry_for_test(
            kinder=self.kid,
            beschreibung=description,
            added_by=self.user,
        )

    def test_first_aid_pages_keep_photo_shape_order_privacy_and_twenty_entry_cap(self):
        storage = MemoryPhotoStorage()
        entries = []
        with use_photo_storage(storage):
            for entry_index in range(21):
                entry = self.create_entry(
                    f"Private medizinische Beschreibung {entry_index}"
                )
                entries.append(entry)
                add_first_aid_photo(
                    entry,
                    storage,
                    position=1,
                    size=(20, 32),
                )
                add_first_aid_photo(
                    entry,
                    storage,
                    position=0,
                    size=(31, 19),
                )

            initial_response = self.client.get(self.contract_url())
            initial = initial_response.json()["activity"]["first_aid"]
            continuation_response = self.client.get(self.contract_url(
                activity="first_aid",
                cursor=initial["next_cursor"],
            ))

        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(len(initial["items"]), 20)
        self.assertEqual(initial["limit"], 20)
        self.assertTrue(initial["has_more"])
        newest = initial["items"][0]
        self.assertEqual(newest["id"], entries[-1].id)
        newest_stamp = entries[-1].date_added.strftime("%d.%m.%Y %H:%M")
        self.assertEqual(
            [photo["alt"] for photo in newest["photos"]],
            [
                f"EH-Foto 1 von Grace Hopper, EH-Eintrag vom {newest_stamp}",
                f"EH-Foto 2 von Grace Hopper, EH-Eintrag vom {newest_stamp}",
            ],
        )
        self.assertEqual(
            [photo["width"] for photo in newest["photos"]],
            [31, 20],
        )
        self.assertTrue(
            all(
                set(photo) == PHOTO_FIELDS
                for item in initial["items"]
                for photo in item["photos"]
            )
        )

        continuation = continuation_response.json()["activity"]["first_aid"]
        self.assertEqual(continuation_response.status_code, 200)
        self.assertEqual([item["id"] for item in continuation["items"]], [entries[0].id])
        self.assertEqual(len(continuation["items"][0]["photos"]), 2)
        self.assertFalse(continuation["has_more"])
        self.assertIsNone(continuation["next_cursor"])

        response_text = initial_response.content.decode()
        for photo in entries[-1].fotos.all():
            self.assertNotIn(photo.datei.name, response_text)
            self.assertNotIn(photo.checksum, response_text)

    def test_dashboard_photo_queries_and_payload_stay_bounded_as_history_grows(self):
        storage = MemoryPhotoStorage()
        with use_photo_storage(storage):
            for entry_index in range(25):
                entry = self.create_entry(f"Bestehender EH-Eintrag {entry_index}")
                for position in range(5):
                    add_first_aid_photo(entry, storage, position=position)
            before = measure_http_get(self.client, self.contract_url())

            for entry_index in range(200):
                entry = self.create_entry(f"Historischer EH-Eintrag {entry_index}")
                for position in range(5):
                    add_first_aid_photo(entry, storage, position=position)
            after = measure_http_get(self.client, self.contract_url())

        first_aid = after.response.json()["activity"]["first_aid"]
        self.assertEqual(after.status_code, 200)
        self.assertEqual(len(first_aid["items"]), 20)
        self.assertEqual(
            sum(len(item["photos"]) for item in first_aid["items"]),
            100,
        )
        self.assertTrue(first_aid["has_more"])
        self.assertQueryCountAtMost(after, 13)
        self.assertQueryGrowthAtMost(before, after, 0)
        self.assertLess(after.response_bytes - before.response_bytes, 3_000)
