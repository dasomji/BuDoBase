import json
from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.first_aid_tests.fixtures import create_first_aid_entry_for_test
from budo_app.models import (
    ErsteHilfeEintrag,
    Geld,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Notizen,
    Schwerpunkte,
    Schwerpunktzeit,
    SpezialFamilien,
    Turnus,
)


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
    "focus_assignments",
    "happy_cleaning_number",
    "happy_cleaning_assignments",
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
    "first_aid_entries",
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
        self.special_family = SpezialFamilien.objects.create(
            name="Biberhaus",
            turnus=self.turnus,
        )
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
            spezial_familien=self.special_family,
            happy_cleaning_number=42,
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
        self.period_w1 = self.turnus.schwerpunktzeit_set.get(woche="w1")
        self.period_w2 = self.turnus.schwerpunktzeit_set.get(woche="w2")
        self.period_w1.swp_beginn = date(2026, 7, 9)
        self.period_w1.dauer = 3
        self.period_w1.save(update_fields=["swp_beginn", "dauer"])
        self.period_w2.swp_beginn = date(2026, 7, 2)
        self.period_w2.dauer = 2
        self.period_w2.save(update_fields=["swp_beginn", "dauer"])
        self.period_empty = Schwerpunktzeit.objects.create(
            turnus=self.turnus,
            woche="u",
            swp_beginn=date(2026, 7, 6),
            dauer=1,
        )
        self.alpha_lower = Schwerpunkte.objects.create(
            swp_name="alpha",
            schwerpunktzeit=self.period_w1,
        )
        self.alpha_upper = Schwerpunkte.objects.create(
            swp_name="Alpha",
            schwerpunktzeit=self.period_w1,
        )
        self.wald = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=self.period_w2,
        )
        self.kid.schwerpunkte.add(
            self.alpha_lower,
            self.alpha_upper,
            self.wald,
        )

        self.event_station = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
        )
        self.event_excused = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
        )
        self.event_unassigned = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=3,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event_station,
            name="Küche <Nord>",
            max_kids=4,
            meeting_point="Hof",
            position=1,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event_station,
            station=self.station,
            child=self.kid,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event_excused,
            station=None,
            target_kind=HappyCleaningAssignment.TargetKind.EXCUSED,
            child=self.kid,
        )
        self.foreign_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
        )
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
        self.first_aid_older = create_first_aid_entry_for_test(
            kinder=self.kid,
            beschreibung="Hand gekühlt",
            added_by=self.user,
        )
        self.first_aid_newer = create_first_aid_entry_for_test(
            kinder=self.kid,
            beschreibung="Knie verbunden",
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
        create_first_aid_entry_for_test(
            kinder=self.other_kid,
            beschreibung="Fremder EH-Eintrag",
            added_by=self.user,
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
        self.assertEqual(kid["special_family"], "Biberhaus")
        self.assertNotIn("focus_w1", kid)
        self.assertNotIn("focus_w2", kid)
        self.assertEqual(kid["happy_cleaning_number"], 42)
        self.assertEqual(
            kid["focus_assignments"],
            [
                {
                    "period_id": self.period_w2.id,
                    "code": "w2",
                    "label": "Woche 2 (2 Tage)",
                    "focuses": [{"id": self.wald.id, "label": "Wald"}],
                },
                {
                    "period_id": self.period_empty.id,
                    "code": "u",
                    "label": "unklar (1 Tag)",
                    "focuses": [],
                },
                {
                    "period_id": self.period_w1.id,
                    "code": "w1",
                    "label": "Woche 1 (3 Tage)",
                    "focuses": [
                        {"id": self.alpha_lower.id, "label": "alpha"},
                        {"id": self.alpha_upper.id, "label": "Alpha"},
                    ],
                },
            ],
        )
        self.assertEqual(
            kid["happy_cleaning_assignments"],
            [
                {
                    "event_id": self.event_excused.id,
                    "display_number": 1,
                    "label": "Happy Cleaning 1",
                    "target": {"kind": "excused", "label": "Entschuldigt"},
                },
                {
                    "event_id": self.event_station.id,
                    "display_number": 2,
                    "label": "Happy Cleaning 2",
                    "target": {
                        "kind": "station",
                        "station_id": self.station.id,
                        "label": "Küche <Nord>",
                    },
                },
                {
                    "event_id": self.event_unassigned.id,
                    "display_number": 3,
                    "label": "Happy Cleaning 3",
                    "target": {
                        "kind": "unassigned",
                        "label": "Nicht eingeteilt",
                    },
                },
            ],
        )
        self.assertEqual(kid["social_security_number"], "1234 020712")
        self.assertEqual(kid["emergency_contacts"], "Grace +43 456")
        self.assertEqual(kid["notes"], [{
            "id": self.note.id,
            "text": "Sonnencreme",
            "date": self.note.date_added.isoformat(),
            "day": self.note.date_added.strftime("%d.%m."),
            "author": "kid-detail-user",
            "photos": [],
        }])
        self.assertEqual(kid["first_aid_entries"], [
            {
                "id": self.first_aid_newer.id,
                "text": "Knie verbunden",
                "date": self.first_aid_newer.date_added.isoformat(),
                "day": self.first_aid_newer.date_added.strftime("%d.%m."),
                "author": "kid-detail-user",
                "photos": [],
            },
            {
                "id": self.first_aid_older.id,
                "text": "Hand gekühlt",
                "date": self.first_aid_older.date_added.isoformat(),
                "day": self.first_aid_older.date_added.strftime("%d.%m."),
                "author": "kid-detail-user",
                "photos": [],
            },
        ])
        self.assertNotContains(response, "Fremder EH-Eintrag")
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
        self.assertEqual(
            kid.get("focus_assignments"),
            [
                {
                    "period_id": self.period_w2.id,
                    "code": "w2",
                    "label": "Woche 2 (2 Tage)",
                    "focuses": [{"id": self.wald.id, "label": "Wald"}],
                },
                {
                    "period_id": self.period_empty.id,
                    "code": "u",
                    "label": "unklar (1 Tag)",
                    "focuses": [],
                },
                {
                    "period_id": self.period_w1.id,
                    "code": "w1",
                    "label": "Woche 1 (3 Tage)",
                    "focuses": [
                        {"id": self.alpha_lower.id, "label": "alpha"},
                        {"id": self.alpha_upper.id, "label": "Alpha"},
                    ],
                },
            ],
        )
        self.assertNotContains(response, "ZZZ Fremder Schwerpunkt")

    def test_foreign_station_corruption_projects_safe_unassigned_target(self):
        foreign_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.foreign_event,
            name="FOREIGN-STATION-PRIVATE",
            max_kids=99,
            meeting_point="Foreign",
            position=1,
        )
        HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event_station,
            child=self.kid,
        ).update(station_id=foreign_station.id)

        response = self.client.get(self.contract_url(self.kid))

        self.assertEqual(response.status_code, 200)
        assignments = response.json()["kids"][0][
            "happy_cleaning_assignments"
        ]
        self.assertEqual(
            assignments,
            [
                {
                    "event_id": self.event_excused.id,
                    "display_number": 1,
                    "label": "Happy Cleaning 1",
                    "target": {"kind": "excused", "label": "Entschuldigt"},
                },
                {
                    "event_id": self.event_station.id,
                    "display_number": 2,
                    "label": "Happy Cleaning 2",
                    "target": {
                        "kind": "unassigned",
                        "label": "Nicht eingeteilt",
                    },
                },
                {
                    "event_id": self.event_unassigned.id,
                    "display_number": 3,
                    "label": "Happy Cleaning 3",
                    "target": {
                        "kind": "unassigned",
                        "label": "Nicht eingeteilt",
                    },
                },
            ],
        )
        self.assertNotIn(
            foreign_station.id,
            [
                assignment["target"].get("station_id")
                for assignment in assignments
            ],
        )
        self.assertNotContains(response, "FOREIGN-STATION-PRIVATE")

    def test_returns_empty_dynamic_assignments_and_a_null_cleaning_number(self):
        self.turnus.schwerpunktzeit_set.all().delete()
        self.turnus.happy_cleanings.all().delete()
        self.kid.happy_cleaning_number = None
        self.kid.save(update_fields=["happy_cleaning_number"])

        response = self.client.get(self.contract_url(self.kid))

        self.assertEqual(response.status_code, 200)
        kid = response.json()["kids"][0]
        self.assertEqual(kid.get("focus_assignments"), [])
        self.assertEqual(kid.get("happy_cleaning_assignments"), [])
        self.assertIn("happy_cleaning_number", kid)
        self.assertIsNone(kid["happy_cleaning_number"])


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

    def test_first_aid_write_requires_text_and_refreshes_the_detail_contract(self):
        empty = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "interaction_kind": "first_aid",
                "erste_hilfe_beschreibung": "   ",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(empty.status_code, 422)
        self.assertEqual(
            empty.json()["errors"],
            ["Bitte eine Beschreibung eingeben."],
        )
        self.assertFalse(ErsteHilfeEintrag.objects.exists())

        accepted = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "interaction_kind": "first_aid",
                "erste_hilfe_beschreibung": "Knie gereinigt und verbunden",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(accepted.status_code, 200)
        entry = ErsteHilfeEintrag.objects.get()
        self.assertEqual(entry.kinder, self.kid)
        self.assertEqual(entry.added_by, self.user)
        self.assertEqual(entry.beschreibung, "Knie gereinigt und verbunden")
        self.assertEqual(self.detail_payload()["first_aid_entries"], [{
            "id": entry.id,
            "text": "Knie gereinigt und verbunden",
            "date": entry.date_added.isoformat(),
            "day": entry.date_added.strftime("%d.%m."),
            "author": "kid-mutation-user",
            "photos": [],
        }])

    def test_first_aid_write_rejects_a_kid_outside_the_active_turnus(self):
        other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Turnus",
            kid_birthday=date(2012, 8, 2),
            turnus=other_turnus,
        )

        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{other_kid.id}",
                "interaction_kind": "first_aid",
                "erste_hilfe_beschreibung": "Darf nicht gespeichert werden",
            },
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ErsteHilfeEintrag.objects.exists())

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
