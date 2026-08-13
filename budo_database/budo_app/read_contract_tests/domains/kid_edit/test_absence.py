from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Turnus,
)


class KidEditAbsenceContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=163,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kid-edit-absence-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.kid = Kinder.objects.create(
            kid_index="ABSENCE-163-07",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
            edit_version=7,
            happy_cleaning_number=23,
        )
        event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
        )
        station = HappyCleaningStation.objects.create(
            happy_cleaning=event,
            name="Küche",
            max_kids=4,
            meeting_point="Hof",
            position=1,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=event,
            station=station,
            child=self.kid,
            version=3,
        )

    def route_url(self, key):
        return (
            reverse("route-data-api", kwargs={"contract_key": key})
            + f"?id={self.kid.id}"
        )

    def persisted_state(self):
        return {
            "kid": Kinder.objects.filter(pk=self.kid.id).values(
                "kid_vorname",
                "kid_nachname",
                "edit_version",
                "happy_cleaning_number",
                "happy_cleaning_number_version",
            ).get(),
            "assignments": list(
                HappyCleaningAssignment.objects.filter(child=self.kid)
                .order_by("id")
                .values(
                    "happy_cleaning_id",
                    "station_id",
                    "target_kind",
                    "version",
                )
            ),
            "audit": AuditEvent.objects.count(),
            "ledger": HappyCleaningCommandRequest.objects.count(),
        }

    def test_reads_and_invalid_write_requests_have_no_write_side_effects(self):
        before = self.persisted_state()

        kid_edit_get = self.client.get(self.route_url("kid-edit"))
        kid_detail_get = self.client.get(self.route_url("kid-detail"))
        invalid_write = self.client.post(
            f"/api/kids/{self.kid.id}/edit/",
            data='{"first_name":"Changed"}',
            content_type="application/json",
        )
        route_data_post = self.client.post(
            self.route_url("kid-edit"),
            data='{"first_name":"Changed"}',
            content_type="application/json",
        )

        self.assertEqual(kid_edit_get.status_code, 200)
        self.assertEqual(kid_detail_get.status_code, 200)
        self.assertEqual(invalid_write.status_code, 422)
        self.assertFalse(invalid_write.json()["ok"])
        self.assertEqual(route_data_post.status_code, 405)
        self.assertEqual(self.persisted_state(), before)
