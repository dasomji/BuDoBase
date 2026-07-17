from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from budo_app.models import Kinder, Notizen, SpezialFamilien, Turnus


class ReportContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="reports-user",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.rufname = "Zora"
        self.user.profil.rolle = "o"
        self.user.profil.save()
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=True,
            ausweis=True,
            e_card=False,
            einverstaendnis_erklaerung=True,
            rezeptfreie_medikamente="Ibuprofen",
            rezept_medikamente="Inhalator",
            tetanusimpfung="2024",
            zeckenimpfung="2025",
            illness="Asthma",
            drugs="Notfallspray",
            special_food_description="glutenfrei",
            sozialversicherungsnr="1234 020712",
            notfall_kontakte="Private Kontaktperson",
            anmelder_email="private@example.test",
            anmerkung="Private Notiz",
        )
        self.client.force_login(self.user)

    def contract_url(self, key):
        return reverse("route-data-api", kwargs={"contract_key": key})

    def test_serial_letter_returns_only_its_active_turnus_projection(self):
        response = self.client.get(self.contract_url("serial-letter"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "kids": [
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Lovelace",
                        "id_card": True,
                        "e_card": False,
                        "consent": True,
                        "over_the_counter_medication": "Ibuprofen",
                        "prescription_medication": "Inhalator",
                        "tetanus": "2024",
                        "tick_vaccine": "2025",
                        "illness": "Asthma",
                        "drugs": "Notfallspray",
                        "special_food": "glutenfrei",
                    }
                ]
            },
        )
        response_text = response.content.decode()
        for private_value in (
            "1234 020712",
            "Private Kontaktperson",
            "private@example.test",
            "Private Notiz",
        ):
            self.assertNotIn(private_value, response_text)

    def test_murder_game_contains_only_present_kids_and_active_team(self):
        absent_kid = Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Berta",
            kid_nachname="Absent",
            turnus=self.turnus,
            anwesend=False,
        )
        teammate = User.objects.create_user(username="murder-teamer")
        teammate.profil.turnus = self.turnus
        teammate.profil.rufname = "Aaron"
        teammate.profil.rolle = "b"
        teammate.profil.telefonnummer = "+436641234567"
        teammate.profil.save()
        other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        other_user = User.objects.create_user(username="other-murder-teamer")
        other_user.profil.turnus = other_turnus
        other_user.profil.rufname = "Private Other Teamer"
        other_user.profil.save()

        response = self.client.get(self.contract_url("murder-game"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "kids": [
                    {"id": self.kid.id, "full_name": "Ada Lovelace"},
                ],
                "team": [
                    {
                        "id": teammate.profil.id,
                        "rufname": "Aaron",
                        "role_display": "Betreuer:in",
                    },
                    {
                        "id": self.user.profil.id,
                        "rufname": "Zora",
                        "role_display": "Organisator",
                    },
                ],
            },
        )
        self.assertNotContains(response, absent_kid.kid_vorname)
        self.assertNotContains(response, "Private Other Teamer")
        self.assertNotContains(response, "+436641234567")

    def test_family_contracts_preserve_group_and_kid_order_and_empty_behavior(self):
        alpha_family = SpezialFamilien.objects.create(
            name="Alpha-Haus",
            turnus=self.turnus,
        )
        zeta_family = SpezialFamilien.objects.create(
            name="Zeta-Haus",
            turnus=self.turnus,
        )
        self.kid.budo_family = "L"
        self.kid.spezial_familien = zeta_family
        self.kid.save()
        aaron = Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Aaron",
            kid_nachname="First",
            kid_birthday=date(2013, 7, 1),
            turnus=self.turnus,
            anwesend=False,
            budo_family="S",
            spezial_familien=alpha_family,
        )
        abel = Kinder.objects.create(
            kid_index="T2-3",
            kid_vorname="Abel",
            kid_nachname="Second",
            kid_birthday=date(2014, 7, 1),
            turnus=self.turnus,
            anwesend=True,
            budo_family="S",
            spezial_familien=alpha_family,
        )
        Kinder.objects.create(
            kid_index="T2-4",
            kid_vorname="Unassigned",
            kid_nachname="Hidden",
            turnus=self.turnus,
        )

        families = self.client.get(self.contract_url("families"))
        special_families = self.client.get(
            self.contract_url("special-families"),
        )

        self.assertEqual(families.status_code, 200)
        self.assertEqual(
            families.json(),
            {
                "kids": [
                    {
                        "id": aaron.id,
                        "full_name": "Aaron First",
                        "present": False,
                        "age": 13.0,
                        "budo_family": "S",
                    },
                    {
                        "id": abel.id,
                        "full_name": "Abel Second",
                        "present": True,
                        "age": 12.0,
                        "budo_family": "S",
                    },
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Lovelace",
                        "present": True,
                        "age": 14.0,
                        "budo_family": "L",
                    },
                ]
            },
        )
        self.assertEqual(
            special_families.json(),
            {
                "kids": [
                    {
                        "id": aaron.id,
                        "full_name": "Aaron First",
                        "present": False,
                        "age": 13.0,
                        "special_family": "Alpha-Haus",
                    },
                    {
                        "id": abel.id,
                        "full_name": "Abel Second",
                        "present": True,
                        "age": 12.0,
                        "special_family": "Alpha-Haus",
                    },
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Lovelace",
                        "present": True,
                        "age": 14.0,
                        "special_family": "Zeta-Haus",
                    },
                ]
            },
        )
        self.assertNotContains(families, "Unassigned Hidden")
        self.assertNotContains(special_families, "Unassigned Hidden")

    def test_birthdays_returns_derived_sv_date_without_the_raw_number(self):
        self.kid.anwesend = False
        self.kid.save()
        invalid = Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Berta",
            kid_nachname="Invalid",
            kid_birthday=None,
            turnus=self.turnus,
            anwesend=True,
            sozialversicherungsnr="1234 310226",
        )

        response = self.client.get(self.contract_url("birthdays"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "kids": [
                    {
                        "id": self.kid.id,
                        "full_name": "Ada Lovelace",
                        "present": False,
                        "birthday": "2012-07-02",
                        "sv_birthday": "2012-07-02",
                    },
                    {
                        "id": invalid.id,
                        "full_name": "Berta Invalid",
                        "present": True,
                        "birthday": None,
                        "sv_birthday": None,
                    },
                ]
            },
        )
        self.assertNotContains(response, "1234 020712")
        self.assertNotContains(response, "1234 310226")
        for private_field in (
            "social_security_number",
            "emergency_contacts",
            "registrant_email",
            "note",
            "notes",
            "transactions",
        ):
            self.assertNotContains(response, private_field)

    def test_kid_count_retains_checked_in_and_total_calculation(self):
        Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Berta",
            kid_nachname="Absent",
            turnus=self.turnus,
            anwesend=False,
        )
        Kinder.objects.create(
            kid_index="T2-3",
            kid_vorname="Clara",
            kid_nachname="Unknown",
            turnus=self.turnus,
            anwesend=None,
        )
        other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Present",
            turnus=other_turnus,
            anwesend=True,
        )

        response = self.client.get(self.contract_url("kid-count"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"totals": {"checked_in": 1, "kids": 3}},
        )

    def test_all_kid_report_contracts_exclude_other_turnus_records(self):
        other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        other_family = SpezialFamilien.objects.create(
            name="Private Other Family",
            turnus=other_turnus,
        )
        Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Private Other",
            kid_nachname="Kind",
            turnus=other_turnus,
            anwesend=True,
            budo_family="XL",
            spezial_familien=other_family,
            sozialversicherungsnr="9876 030813",
            illness="Private other illness",
        )

        for key in (
            "birthdays",
            "families",
            "murder-game",
            "serial-letter",
            "special-families",
        ):
            with self.subTest(key=key):
                response = self.client.get(self.contract_url(key))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "Private Other")
                self.assertNotContains(response, "Private other illness")
                self.assertNotContains(response, "9876 030813")

    def test_every_report_requires_authentication_and_handles_no_turnus(self):
        keys = (
            "birthdays",
            "families",
            "kid-count",
            "murder-game",
            "serial-letter",
            "special-families",
        )
        self.client.logout()
        for key in keys:
            with self.subTest(key=key, state="unauthenticated"):
                self.assertEqual(
                    self.client.get(self.contract_url(key)).status_code,
                    403,
                )

        user_without_turnus = User.objects.create_user(username="no-turnus")
        self.client.force_login(user_without_turnus)
        for key in keys:
            with self.subTest(key=key, state="no-turnus"):
                response = self.client.get(self.contract_url(key))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json(),
                    {"totals": {"checked_in": 0, "kids": 0}}
                    if key == "kid-count"
                    else {
                        "kids": [],
                        "team": [],
                    }
                    if key == "murder-game"
                    else {"kids": []},
                )


class BirthdayActionContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="birthday-action",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2011, 1, 1),
            turnus=self.turnus,
            sozialversicherungsnr="1234 020712",
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf_token = self.client.get(
            reverse("bootstrap-api"),
        ).json()["csrf_token"]

    def post_form(self, payload):
        return self.client.post(
            reverse("form-submit-api"),
            payload,
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

    def test_birthday_note_saves_and_preserves_redirect_fallback(self):
        response = self.post_form(
            {
                "_target": "/kindergeburtstage/",
                "kid_id": self.kid.id,
                "notiz": "SV-Geburtstag: 02.07.2012",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"ok": True, "redirect": "/kindergeburtstage/"},
        )
        note = Notizen.objects.get(kinder=self.kid)
        self.assertEqual(note.notiz, "SV-Geburtstag: 02.07.2012")
        self.assertEqual(note.added_by, self.user)

    def test_update_action_validates_method_updates_contract_and_queues_message(self):
        get_response = self.client.get(reverse("update_birthdays_from_sv"))

        self.assertEqual(get_response.status_code, 405)

        response = self.post_form(
            {"_target": "/update-birthdays-from-sv/"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"ok": True, "redirect": "/kindergeburtstage/"},
        )
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.kid_birthday, date(2012, 7, 2))
        focused = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "birthdays"},
            ),
        ).json()
        self.assertEqual(focused["kids"][0]["birthday"], "2012-07-02")
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["messages"],
            [
                {
                    "text": "Successfully updated 1 birthdays from SV numbers.",
                    "tags": "success",
                }
            ],
        )

    def test_birthday_actions_reject_missing_csrf_and_cross_turnus_kids(self):
        missing_csrf = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/update-birthdays-from-sv/"},
        )
        self.assertEqual(missing_csrf.status_code, 403)

        other_turnus = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Kind",
            turnus=other_turnus,
        )
        rejected = self.post_form(
            {
                "_target": "/kindergeburtstage/",
                "kid_id": other_kid.id,
                "notiz": "Must not save",
            },
        )

        self.assertEqual(rejected.status_code, 404)
        self.assertFalse(Notizen.objects.filter(kinder=other_kid).exists())

    def test_invalid_sv_number_preserves_info_and_warning_messages(self):
        self.kid.sozialversicherungsnr = "1234 310226"
        self.kid.save()

        response = self.post_form(
            {"_target": "/update-birthdays-from-sv/"},
        )

        self.assertEqual(response.status_code, 200)
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.kid_birthday, date(2011, 1, 1))
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["messages"],
            [
                {
                    "text": "No birthdays needed updating.",
                    "tags": "info",
                },
                {
                    "text": "1 errors occurred during update. Check logs for details.",
                    "tags": "warning",
                },
            ],
        )
