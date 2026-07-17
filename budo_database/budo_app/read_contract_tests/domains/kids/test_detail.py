import json
from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.models import Geld, Kinder, Notizen, Schwerpunkte, Turnus


DETAIL_FIELDS = {
    "id",
    "full_name",
    "present",
    "sex",
    "age",
    "birthday",
    "weeks",
    "siblings",
    "tent_request",
    "budo_experience",
    "budo_family",
    "special_family",
    "focus_w1",
    "focus_w2",
    "social_security_number",
    "illness",
    "drugs",
    "vegetarian",
    "special_food",
    "swimmer",
    "consent",
    "over_the_counter_medication",
    "prescription_medication",
    "tetanus",
    "tick_vaccine",
    "organization",
    "registrant_name",
    "registrant_email",
    "registrant_phone",
    "insured_with",
    "emergency_contacts",
    "booking_note",
    "note",
    "notes",
    "transactions",
    "remaining_money",
    "deposit",
}


class KidDetailContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(
            username="kid-detail-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=True,
            sex="weiblich",
            turnus_dauer=2,
            geschwister="Charles",
            zeltwunsch="Grace",
            budo_erfahrung=True,
            budo_family="M",
            sozialversicherungsnr="1234 020712",
            illness="Allergie",
            drugs="Asthmaspray",
            vegetarisch="ja",
            special_food_description="glutenfrei",
            swimmer="gut",
            einverstaendnis_erklaerung=True,
            rezeptfreie_medikamente="Ibuprofen",
            rezept_medikamente="Penicillin",
            tetanusimpfung="Ja",
            zeckenimpfung="Nein",
            anmelde_organisation="BuDo",
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            anmelder_email="ann@example.test",
            anmelder_mobil="+43 123",
            hauptversichert_bei="Ann Lovelace",
            notfall_kontakte="Grace +43 456",
            anmerkung_buchung="Buchungsnotiz",
            anmerkung="Teamnotiz",
            pfand=2,
        )
        for week, name in (("w1", "Theater"), ("w2", "Wald")):
            focus_time = self.turnus.schwerpunktzeit_set.get(woche=week)
            focus = Schwerpunkte.objects.create(
                swp_name=name,
                schwerpunktzeit=focus_time,
            )
            self.kid.schwerpunkte.add(focus)
        self.note = Notizen.objects.create(
            kinder=self.kid,
            notiz="Sonnencreme",
            added_by=self.user,
        )
        self.transaction = Geld.objects.create(
            kinder=self.kid,
            amount=10,
            added_by=self.user,
        )
        self.other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Turnus",
            kid_birthday=date(2012, 8, 2),
            turnus=self.other_turnus,
            sozialversicherungsnr="private-other-turnus",
        )

    def contract_url(self, kid):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "kid-detail"},
        ) + f"?id={kid.id}"

    def test_returns_the_explicit_authorized_projection_for_one_kind(self):
        response = self.client.get(self.contract_url(self.kid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"kids"})
        self.assertEqual(len(response.json()["kids"]), 1)
        kid = response.json()["kids"][0]
        self.assertEqual(set(kid), DETAIL_FIELDS)
        self.assertEqual(kid["full_name"], "Ada Lovelace")
        self.assertEqual(kid["focus_w1"], "Theater")
        self.assertEqual(kid["focus_w2"], "Wald")
        self.assertEqual(kid["social_security_number"], "1234 020712")
        self.assertEqual(kid["emergency_contacts"], "Grace +43 456")
        self.assertEqual(kid["notes"], [{
            "id": self.note.id,
            "text": "Sonnencreme",
            "date": self.note.date_added.isoformat(),
            "day": self.note.date_added.strftime("%d.%m."),
            "author": "kid-detail-user",
        }])
        self.assertEqual(kid["transactions"], [{
            "id": self.transaction.id,
            "amount": 10.0,
            "date": self.transaction.date_added.isoformat(),
            "day": self.transaction.date_added.strftime("%d.%m."),
            "author": "kid-detail-user",
        }])
        self.assertEqual(kid["remaining_money"], 9.5)
        self.assertEqual(kid["deposit"], 2)

    def test_rejects_a_kind_outside_the_active_turnus(self):
        response = self.client.get(self.contract_url(self.other_kid))

        self.assertEqual(response.status_code, 404)

    def test_ignores_a_cross_turnus_focus_linked_to_the_kind(self):
        foreign_focus = Schwerpunkte.objects.create(
            swp_name="ZZZ Fremder Schwerpunkt",
            schwerpunktzeit=self.other_turnus.schwerpunktzeit_set.get(
                woche="w1",
            ),
        )
        self.kid.schwerpunkte.add(foreign_focus)

        response = self.client.get(self.contract_url(self.kid))

        self.assertEqual(response.status_code, 200)
        kid = response.json()["kids"][0]
        self.assertEqual(kid["focus_w1"], "Theater")
        self.assertNotContains(response, "ZZZ Fremder Schwerpunkt")


class KidDetailMutationContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="kid-mutation-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            pfand=1,
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        bootstrap = self.client.get(reverse("bootstrap-api"))
        self.csrf_token = bootstrap.json()["csrf_token"]

    def detail_payload(self):
        response = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "kid-detail"},
            ),
            {"id": self.kid.id},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["kids"][0]

    def test_existing_note_money_and_pfand_writes_refresh_coherent_detail_data(self):
        note_response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "notiz": "Neue Notiz",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(note_response.status_code, 200)
        self.assertEqual(
            [note["text"] for note in self.detail_payload()["notes"]],
            ["Neue Notiz"],
        )

        money_response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "amount": "5",
                "money_action": "topup",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(money_response.status_code, 200)
        money_payload = self.detail_payload()
        self.assertEqual(
            [transaction["amount"] for transaction in money_payload["transactions"]],
            [5.0],
        )
        self.assertEqual(money_payload["remaining_money"], 4.75)

        pfand_response = self.client.post(
            reverse("update_pfand"),
            data=json.dumps({"id": self.kid.id, "action": "increase"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(pfand_response.status_code, 200)
        pfand_payload = self.detail_payload()
        self.assertEqual(pfand_payload["deposit"], 2)
        self.assertEqual(pfand_payload["remaining_money"], 4.5)

    def test_pfand_write_still_requires_csrf(self):
        response = self.client.post(
            reverse("update_pfand"),
            data=json.dumps({"id": self.kid.id, "action": "increase"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.pfand, 1)
