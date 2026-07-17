from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import Kinder, Schwerpunkte, SpezialFamilien, Turnus


DIRECTORY_FIELDS = {
    "id",
    "full_name",
    "present",
    "budo_family",
    "special_family",
    "sex_short",
    "age",
    "birthday_during_turnus",
    "weeks",
    "focus_w1",
    "focus_w2",
    "siblings",
    "tent_request",
    "food",
    "drugs",
    "illness",
    "note",
    "booking_note",
}


class KidsDirectoryContractTests(TestCase):
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
            username="kids-directory-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.force_login(self.user)
        family = SpezialFamilien.objects.create(
            name="Biberhaus",
            turnus=self.turnus,
        )
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=False,
            budo_family="M",
            spezial_familien=family,
            sex="weiblich",
            turnus_dauer=2,
            geschwister="Charles",
            zeltwunsch="Grace",
            vegetarisch="ja",
            special_food_description="glutenfrei",
            drugs="Asthmaspray",
            illness="Allergie",
            anmerkung="Teamnotiz",
            anmerkung_buchung="Buchungsnotiz",
            sozialversicherungsnr="1234 020712",
            notfall_kontakte="Private Kontaktperson",
        )
        for week, name in (("w1", "Theater"), ("w2", "Wald")):
            focus_time = self.turnus.schwerpunktzeit_set.get(woche=week)
            focus = Schwerpunkte.objects.create(
                swp_name=name,
                schwerpunktzeit=focus_time,
            )
            self.kid.schwerpunkte.add(focus)
        Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Turnus",
            kid_birthday=date(2012, 8, 2),
            turnus=self.other_turnus,
            anmelder_vorname="Private",
            anmelder_email="other@example.test",
        )

    def contract_url(self):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "kids-directory"},
        )

    def test_returns_only_the_active_turnus_table_projection(self):
        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"kids"})
        self.assertEqual(len(response.json()["kids"]), 1)
        kid = response.json()["kids"][0]
        self.assertEqual(set(kid), DIRECTORY_FIELDS)
        self.assertEqual(
            kid,
            {
                "id": self.kid.id,
                "full_name": "Ada Lovelace",
                "present": False,
                "budo_family": "M",
                "special_family": "Biberhaus",
                "sex_short": "♀",
                "age": 14.0,
                "birthday_during_turnus": True,
                "weeks": 2,
                "focus_w1": "Theater",
                "focus_w2": "Wald",
                "siblings": "Charles",
                "tent_request": "Grace",
                "food": "🥦 - glutenfrei",
                "drugs": "Asthmaspray",
                "illness": "Allergie",
                "note": "Teamnotiz",
                "booking_note": "Buchungsnotiz",
            },
        )
        for private_field in (
            "social_security_number",
            "emergency_contacts",
            "registrant_email",
            "notes",
            "transactions",
            "remaining_money",
            "deposit",
        ):
            self.assertNotIn(private_field, kid)

    def test_preserves_the_empty_directory_behavior(self):
        Kinder.objects.filter(turnus=self.turnus).delete()

        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"kids": []})

    def test_ignores_a_cross_turnus_focus_linked_to_an_active_kind(self):
        foreign_focus = Schwerpunkte.objects.create(
            swp_name="ZZZ Fremder Schwerpunkt",
            schwerpunktzeit=self.other_turnus.schwerpunktzeit_set.get(
                woche="w1",
            ),
        )
        self.kid.schwerpunkte.add(foreign_focus)

        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        kid = response.json()["kids"][0]
        self.assertEqual(kid["focus_w1"], "Theater")
        self.assertNotContains(response, "ZZZ Fremder Schwerpunkt")
