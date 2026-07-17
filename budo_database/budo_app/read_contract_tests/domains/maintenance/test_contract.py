import os
from datetime import date
from unittest.mock import patch

import pandas as pd
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
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


class MaintenanceContractTests(TestCase):
    def setUp(self):
        self.older_turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2025, 7, 1),
        )
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="maintenance-user")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        Kinder.objects.create(
            kid_index="PRIVATE-1",
            kid_vorname="Privates",
            kid_nachname="Kind",
            turnus=self.turnus,
        )
        self.client.force_login(self.user)

    def contract_url(self, key, *, turnus=None):
        url = reverse("route-data-api", kwargs={"contract_key": key})
        return f"{url}?id={turnus.id}" if turnus else url

    def test_turnus_list_returns_only_the_existing_form_rows(self):
        response = self.client.get(self.contract_url("turnus-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "turnuses": [
                {
                    "id": self.turnus.id,
                    "label": "T2-2026",
                    "number": 2,
                    "start": "2026-07-01",
                },
                {
                    "id": self.older_turnus.id,
                    "label": "T1-2025",
                    "number": 1,
                    "start": "2025-07-01",
                },
            ],
        })
        self.assertNotContains(response, "Privates Kind")
        self.assertNotIn("kids", response.json())

    def test_turnus_upload_returns_only_the_selected_form_values(self):
        response = self.client.get(
            self.contract_url("turnus-upload", turnus=self.turnus),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "turnuses": [{
                "id": self.turnus.id,
                "label": "T2-2026",
                "number": 2,
                "start": "2026-07-01",
            }],
        })
        self.assertNotContains(response, "Privates Kind")

    def test_special_upload_has_no_unrelated_domain_data(self):
        response = self.client.get(self.contract_url("special-upload"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})
        self.assertNotContains(response, "Privates Kind")

    def test_turnus_upload_rejects_missing_invalid_and_unknown_identifiers(self):
        missing = self.client.get(self.contract_url("turnus-upload"))
        invalid = self.client.get(
            self.contract_url("turnus-upload") + "?id=not-a-number",
        )
        unknown = self.client.get(
            self.contract_url("turnus-upload") + "?id=999999",
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invalid.status_code, 404)
        self.assertEqual(unknown.status_code, 404)

    def test_all_maintenance_contracts_require_authentication(self):
        self.client.logout()

        responses = [
            self.client.get(self.contract_url("turnus-list")),
            self.client.get(
                self.contract_url("turnus-upload", turnus=self.turnus),
            ),
            self.client.get(self.contract_url("special-upload")),
        ]

        self.assertEqual([response.status_code for response in responses], [
            403,
            403,
            403,
        ])


@override_settings(STORAGES=TEST_STORAGES)
class MaintenanceMultipartWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="maintenance-uploader")
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf_token = self.client.get(
            reverse("bootstrap-api"),
        ).json()["csrf_token"]

    def workbook(self, name, content):
        return SimpleUploadedFile(
            name,
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    @patch("budo_app.excel_views.process_excel")
    def test_turnus_creation_preserves_multipart_file_csrf_message_and_redirect(
        self,
        process_excel_mock,
    ):
        uploaded_content = b"new turnus workbook bytes"

        def inspect_workbook(turnus):
            self.assertEqual(
                os.path.basename(turnus.uploadedFile.name),
                "turnus-neu.xlsx",
            )
            with turnus.uploadedFile.open("rb") as workbook:
                self.assertEqual(workbook.read(), uploaded_content)

        process_excel_mock.side_effect = inspect_workbook
        denied = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/upload/",
                "turnus_nr": "3",
                "turnus_beginn": "2027-07-01",
                "uploadedFile": self.workbook(
                    "turnus-neu.xlsx",
                    uploaded_content,
                ),
            },
        )
        accepted = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/upload/",
                "turnus_nr": "3",
                "turnus_beginn": "2027-07-01",
                "uploadedFile": self.workbook(
                    "turnus-neu.xlsx",
                    uploaded_content,
                ),
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json(), {
            "ok": True,
            "redirect": "/upload/",
        })
        created = Turnus.objects.get(turnus_nr=3)
        self.assertTrue(created.uploadedFile.storage.exists(
            created.uploadedFile.name,
        ))
        process_excel_mock.assert_called_once_with(created)
        first_bootstrap = self.client.get(reverse("bootstrap-api")).json()
        second_bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertEqual(first_bootstrap["messages"], [{
            "text": "Excel-Datei wurde erfolgreich verarbeitet.",
            "tags": "success",
        }])
        self.assertEqual(second_bootstrap["messages"], [])

    @patch("budo_app.excel_views.process_excel")
    def test_selected_turnus_upload_preserves_file_and_redirect(
        self,
        process_excel_mock,
    ):
        uploaded_content = b"replacement workbook bytes"

        def inspect_workbook(turnus):
            self.assertEqual(
                os.path.basename(turnus.uploadedFile.name),
                "ersatz.xlsx",
            )
            with turnus.uploadedFile.open("rb") as workbook:
                self.assertEqual(workbook.read(), uploaded_content)

        process_excel_mock.side_effect = inspect_workbook
        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/upload_excel/{self.turnus.id}/",
                "turnus_nr": "2",
                "turnus_beginn": "2026-07-01",
                "uploadedFile": self.workbook(
                    "ersatz.xlsx",
                    uploaded_content,
                ),
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "ok": True,
            "redirect": "/upload/",
        })
        self.turnus.refresh_from_db()
        self.assertEqual(
            os.path.basename(self.turnus.uploadedFile.name),
            "ersatz.xlsx",
        )
        process_excel_mock.assert_called_once()
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["messages"],
            [{
                "text": "Excel-Datei wurde erfolgreich verarbeitet.",
                "tags": "success",
            }],
        )

    def test_turnus_and_special_upload_validation_errors_remain_in_context(self):
        invalid_turnus = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/upload/",
                "turnus_nr": "4",
                "turnus_beginn": "not-a-date",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        invalid_special = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/upload_spezialfamilien/"},
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(invalid_turnus.status_code, 422)
        self.assertFalse(invalid_turnus.json()["ok"])
        self.assertTrue(invalid_turnus.json()["errors"])
        self.assertFalse(Turnus.objects.filter(turnus_nr=4).exists())
        self.assertEqual(invalid_special.status_code, 422)
        self.assertFalse(invalid_special.json()["ok"])
        self.assertTrue(invalid_special.json()["errors"])

    @patch("budo_app.views.pd.read_excel")
    def test_special_family_upload_preserves_file_content_message_and_redirect(
        self,
        read_excel_mock,
    ):
        kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Kind",
            turnus=self.turnus,
        )
        uploaded_content = b"special family workbook bytes"

        def inspect_workbook(workbook):
            self.assertEqual(workbook.name, "familien.xlsx")
            self.assertEqual(workbook.read(), uploaded_content)
            return pd.DataFrame([{"Index": "T2-1", "Coven": "Falken"}])

        read_excel_mock.side_effect = inspect_workbook
        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": "/upload_spezialfamilien/",
                "csv_file": self.workbook(
                    "familien.xlsx",
                    uploaded_content,
                ),
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "ok": True,
            "redirect": "/upload_spezialfamilien/",
        })
        kid.refresh_from_db()
        family = SpezialFamilien.objects.get(name="Falken")
        self.assertEqual(kid.spezial_familien, family)
        self.assertEqual(family.turnus, self.turnus)
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["messages"],
            [{
                "text": (
                    "Spezialfamilien wurden erfolgreich aktualisiert. "
                    "1 Kinder wurden zugeordnet."
                ),
                "tags": "success",
            }],
        )


@override_settings(STORAGES=TEST_STORAGES)
class MaintenanceContractPerformanceTests(QueryBudgetAssertions, TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="maintenance-performance")
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.fixtures = ActiveTurnusFixtureFactory(self.turnus, self.user)

    def measure_contracts(self):
        base = reverse("route-data-api", kwargs={"contract_key": "turnus-upload"})
        return {
            "turnus-list": measure_http_get(
                self.client,
                reverse(
                    "route-data-api",
                    kwargs={"contract_key": "turnus-list"},
                ),
            ),
            "turnus-upload": measure_http_get(
                self.client,
                f"{base}?id={self.turnus.id}",
            ),
            "special-upload": measure_http_get(
                self.client,
                reverse(
                    "route-data-api",
                    kwargs={"contract_key": "special-upload"},
                ),
            ),
        }

    def test_queries_stay_bounded_and_payloads_beat_the_legacy_graph(self):
        self.fixtures.grow_to(kids=3, focuses=2, team=2, places=1)
        small = self.measure_contracts()

        for index in range(2, 51):
            Turnus.objects.create(
                turnus_nr=index,
                turnus_beginn=date(2026 + index, 7, 1),
            )
        self.fixtures.grow_to(kids=48, focuses=8, team=10, places=6)
        realistic = self.measure_contracts()

        for key in realistic:
            with self.subTest(contract=key):
                self.assertEqual(realistic[key].status_code, 200)
                self.assertQueryCountAtMost(realistic[key], 3)
                self.assertQueryGrowthAtMost(small[key], realistic[key], 0)
                self.assertLess(
                    realistic[key].response_bytes,
                    RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES,
                )
