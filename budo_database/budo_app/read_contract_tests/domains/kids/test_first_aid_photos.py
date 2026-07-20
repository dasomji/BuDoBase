from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import MemoryPhotoStorage, use_photo_storage
from budo_app.first_aid_tests.fixtures import create_first_aid_entry_for_test
from budo_app.models import ErsteHilfeEintrag, Kinder, Turnus
from budo_app.read_contract_tests.first_aid_fixtures import add_first_aid_photo
from budo_app.read_contracts.measurement import (
    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
    QueryBudgetAssertions,
    measure_http_get,
)


PHOTO_FIELDS = {"id", "url", "width", "height", "alt"}


class KidDetailFirstAidPhotoContractTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="kid-photo-contract")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.kid = Kinder.objects.create(
            kid_index="T2-photo-read",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
        )
        self.client.force_login(self.user)

    def contract_url(self):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "kid-detail"},
        ) + f"?id={self.kid.id}"

    def create_entry(self, description):
        return create_first_aid_entry_for_test(
            kinder=self.kid,
            beschreibung=description,
            added_by=self.user,
        )

    def test_exposes_ordered_protected_photo_projection_without_private_metadata(self):
        entry = self.create_entry("Private medizinische Beschreibung")
        storage = MemoryPhotoStorage()
        with use_photo_storage(storage):
            second = add_first_aid_photo(
                entry,
                storage,
                position=1,
                size=(20, 32),
                color=(70, 80, 90),
            )
            first = add_first_aid_photo(
                entry,
                storage,
                position=0,
                size=(31, 19),
                color=(10, 20, 30),
            )

            response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["kids"][0]["first_aid_entries"][0]
        self.assertEqual(item["id"], entry.id)
        entry_stamp = entry.date_added.strftime("%d.%m.%Y %H:%M")
        self.assertEqual(item["photos"], [
            {
                "id": first.id,
                "url": reverse("attachment-media", args=("first-aid", first.id)),
                "width": 31,
                "height": 19,
                "alt": f"EH-Foto 1 von Ada Lovelace, EH-Eintrag vom {entry_stamp}",
            },
            {
                "id": second.id,
                "url": reverse("attachment-media", args=("first-aid", second.id)),
                "width": 20,
                "height": 32,
                "alt": f"EH-Foto 2 von Ada Lovelace, EH-Eintrag vom {entry_stamp}",
            },
        ])
        for photo in item["photos"]:
            self.assertEqual(set(photo), PHOTO_FIELDS)
            self.assertTrue(photo["url"].startswith("/api/attachments/first-aid/"))
            self.assertNotIn("media/first-aid", photo["url"])
        response_text = response.content.decode()
        for private_value in (
            first.datei.name,
            second.datei.name,
            first.checksum,
            second.checksum,
        ):
            self.assertNotIn(private_value, response_text)

    def test_prefetches_photos_with_bounded_queries_and_projection_payload(self):
        storage = MemoryPhotoStorage()
        with use_photo_storage(storage):
            for entry_index in range(2):
                entry = self.create_entry(f"EH-Eintrag {entry_index}")
                add_first_aid_photo(entry, storage, position=0)
            small = measure_http_get(self.client, self.contract_url())

            for entry_index in range(2, 42):
                entry = self.create_entry(f"EH-Eintrag {entry_index}")
                for position in range(5):
                    add_first_aid_photo(entry, storage, position=position)
            realistic = measure_http_get(self.client, self.contract_url())

        payload = realistic.response.json()["kids"][0]["first_aid_entries"]
        self.assertEqual(realistic.status_code, 200)
        self.assertEqual(len(payload), 42)
        self.assertEqual(sum(len(item["photos"]) for item in payload), 202)
        self.assertTrue(all(set(photo) == PHOTO_FIELDS for item in payload for photo in item["photos"]))
        self.assertQueryCountAtMost(realistic, 13)
        self.assertQueryGrowthAtMost(small, realistic, 0)
        self.assertLess(
            realistic.response_bytes,
            RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
        )
