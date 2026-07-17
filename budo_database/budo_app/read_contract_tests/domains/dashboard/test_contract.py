from datetime import date, datetime, timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import (
    BetreuerinnenGeld,
    Geld,
    Kinder,
    Notizen,
    Schwerpunkte,
    Turnus,
)


class DashboardContractTests(TestCase):
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
            username="dashboard-user",
            email="ada@example.test",
            password="secret",
        )
        self.profile = self.user.profil
        self.profile.rufname = "Ada"
        self.profile.turnus = self.turnus
        self.profile.rolle = "b"
        self.profile.essen = "vt"
        self.profile.allergien = "Haselnüsse"
        self.profile.coffee = "Schwarz"
        self.profile.save()
        self.kid = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anwesend=True,
            zug_anreise=True,
            zug_abreise=False,
            sex="weiblich",
            budo_erfahrung=False,
            turnus_dauer=1,
            vegetarisch="ja",
            special_food_description="glutenfrei",
            drugs="Asthmaspray",
            illness="Allergie",
            sozialversicherungsnr="PRIVATE-SVNR",
            notfall_kontakte="PRIVATE-CONTACT",
        )
        self.focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            beschreibung="PRIVATE-DESCRIPTION",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w1"),
        )
        self.focus.betreuende.add(self.profile)
        Geld.objects.create(kinder=self.kid, amount=20, added_by=self.user)
        Geld.objects.create(kinder=self.kid, amount=-2, added_by=self.user)
        BetreuerinnenGeld.objects.create(
            who=self.profile,
            amount=12,
            what="Material",
        )
        self.note = Notizen.objects.create(
            kinder=self.kid,
            notiz="Heute angekommen",
            added_by=self.user,
        )

        other_user = User.objects.create_user(username="other-dashboard-user")
        other_user.profil.turnus = self.other_turnus
        other_user.profil.rufname = "Other private teamer"
        other_user.profil.save()
        other_kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Other",
            kid_nachname="Private",
            turnus=self.other_turnus,
        )
        Notizen.objects.create(
            kinder=other_kid,
            notiz="OTHER-PRIVATE-NOTE",
            added_by=other_user,
        )
        Geld.objects.create(kinder=other_kid, amount=999, added_by=other_user)
        BetreuerinnenGeld.objects.create(
            who=other_user.profil,
            amount=999,
            what="Other private expense",
        )
        self.client.force_login(self.user)

    def contract_url(self):
        return reverse(
            "route-data-api",
            kwargs={"contract_key": "dashboard"},
        )

    def test_returns_only_dashboard_fields_for_the_active_turnus(self):
        response = self.client.get(self.contract_url())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"], {
            "id": self.profile.id,
            "email": "ada@example.test",
            "phone": "",
            "allergies": "Haselnüsse",
            "coffee": "Schwarz",
            "role_display": "Betreuer:in",
            "food_display": "🧀 Vegetarisch",
            "focus_ids": [self.focus.id],
        })
        self.assertEqual(payload["team"], [{
            "id": self.profile.id,
            "rufname": "Ada",
            "food_display": "🧀 Vegetarisch",
            "allergies": "Haselnüsse",
            "money_total": 12.0,
        }])
        self.assertEqual(payload["totals"], {
            "kids": 1,
            "checked_in": 1,
            "train_arrival": 1,
            "train_departure": 0,
            "pocket_money": 18.0,
            "pocket_money_paid": 20.0,
            "team_money": 12.0,
        })
        self.assertEqual(payload["kids"], [{
            "id": self.kid.id,
            "full_name": "Grace Hopper",
            "present": True,
            "age": 14.0,
            "sex": "weiblich",
            "weeks": 1,
            "budo_experience": False,
            "birthday": "2012-07-02",
            "birthday_during_turnus": True,
            "food": "🥦 - glutenfrei",
            "special_food": "glutenfrei",
            "drugs": "Asthmaspray",
            "illness": "Allergie",
        }])
        self.assertEqual(payload["focuses"], [{
            "id": self.focus.id,
            "name": "Wald",
        }])
        self.assertEqual(
            payload["activity"]["notes"]["items"][0],
            {
                "id": self.note.id,
                "text": "Heute angekommen",
                "date": self.note.date_added.isoformat().replace("+00:00", "Z"),
                "author": "dashboard-user",
                "kid_id": self.kid.id,
                "kid": "Grace Hopper",
            },
        )
        response_text = response.content.decode()
        for private_value in (
            "PRIVATE-SVNR",
            "PRIVATE-CONTACT",
            "PRIVATE-DESCRIPTION",
            "OTHER-PRIVATE-NOTE",
            "Other private teamer",
            "999",
        ):
            self.assertNotIn(private_value, response_text)

    def test_activity_uses_stable_independent_keyset_pages(self):
        for index in range(24):
            Notizen.objects.create(
                kinder=self.kid,
                notiz=f"Notiz {index}",
                added_by=self.user,
            )
        for index in range(23):
            Geld.objects.create(
                kinder=self.kid,
                amount=index + 1,
                added_by=self.user,
            )
        tied_time = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        Notizen.objects.filter(kinder=self.kid).update(date_added=tied_time)
        Geld.objects.filter(kinder=self.kid).update(date_added=tied_time)
        expected_note_ids = list(
            Notizen.objects.filter(kinder=self.kid)
            .order_by("-date_added", "-id")
            .values_list("id", flat=True)
        )
        expected_transaction_ids = list(
            Geld.objects.filter(kinder=self.kid)
            .order_by("-date_added", "-id")
            .values_list("id", flat=True)
        )

        initial = self.client.get(self.contract_url()).json()["activity"]

        self.assertEqual(initial["notes"]["limit"], 20)
        self.assertTrue(initial["notes"]["has_more"])
        self.assertEqual(
            [item["id"] for item in initial["notes"]["items"]],
            expected_note_ids[:20],
        )
        self.assertEqual(
            [item["id"] for item in initial["transactions"]["items"]],
            expected_transaction_ids[:20],
        )

        # A newer record arriving between requests must not shift the older page.
        inserted = Notizen.objects.create(
            kinder=self.kid,
            notiz="Später eingetroffen",
            added_by=self.user,
        )
        Notizen.objects.filter(id=inserted.id).update(date_added=tied_time)
        continuation = self.client.get(
            self.contract_url(),
            {
                "activity": "notes",
                "cursor": initial["notes"]["next_cursor"],
            },
        )

        self.assertEqual(continuation.status_code, 200)
        self.assertEqual(set(continuation.json()), {"activity"})
        older_notes = continuation.json()["activity"]["notes"]
        combined_ids = (
            [item["id"] for item in initial["notes"]["items"]]
            + [item["id"] for item in older_notes["items"]]
        )
        self.assertEqual(combined_ids, expected_note_ids)
        self.assertEqual(len(combined_ids), len(set(combined_ids)))
        self.assertFalse(older_notes["has_more"])
        self.assertIsNone(older_notes["next_cursor"])

    def test_rejects_invalid_activity_pagination_inputs(self):
        invalid_stream = self.client.get(
            self.contract_url(),
            {"activity": "private-stream"},
        )
        invalid_cursor = self.client.get(
            self.contract_url(),
            {"activity": "notes", "cursor": "not-a-cursor"},
        )
        unscoped_cursor = self.client.get(
            self.contract_url(),
            {"cursor": "not-a-cursor"},
        )

        self.assertEqual(invalid_stream.status_code, 400)
        self.assertEqual(invalid_cursor.status_code, 400)
        self.assertEqual(unscoped_cursor.status_code, 400)

    def test_subsequent_load_reflects_persisted_money_and_note_mutations(self):
        arriving_kid = Kinder.objects.create(
            kid_index="T2-2",
            kid_vorname="Katherine",
            kid_nachname="Johnson",
            kid_birthday=date(2013, 1, 1),
            turnus=self.turnus,
            anwesend=False,
        )
        before = self.client.get(self.contract_url()).json()

        money_mutation = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "notiz": "Neue Dashboard-Notiz",
                "amount": "5.50",
                "money_action": "deposit",
            },
        )
        attendance_mutation = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/check_in/{arriving_kid.id}",
                "check_in_date": "2026-07-01",
                "notiz": "",
                "amount": "",
            },
        )
        after = self.client.get(self.contract_url()).json()

        self.assertEqual(money_mutation.status_code, 200)
        self.assertEqual(attendance_mutation.status_code, 200)
        self.assertEqual(before["totals"]["pocket_money"], 18.0)
        self.assertEqual(before["totals"]["checked_in"], 1)
        self.assertEqual(after["totals"]["pocket_money"], 23.5)
        self.assertEqual(after["totals"]["pocket_money_paid"], 25.5)
        self.assertEqual(after["totals"]["checked_in"], 2)
        self.assertEqual(
            after["activity"]["notes"]["items"][0]["text"],
            "Neue Dashboard-Notiz",
        )
        self.assertEqual(
            after["activity"]["transactions"]["items"][0]["amount"],
            5.5,
        )

    def test_requires_authentication_and_handles_no_active_turnus_safely(self):
        self.client.logout()
        unauthenticated = self.client.get(self.contract_url())

        self.assertEqual(unauthenticated.status_code, 403)

        no_turnus_user = User.objects.create_user(username="no-turnus-dashboard")
        self.client.force_login(no_turnus_user)
        payload = self.client.get(self.contract_url()).json()

        self.assertEqual(payload["kids"], [])
        self.assertEqual(payload["team"], [])
        self.assertEqual(payload["focuses"], [])
        self.assertEqual(payload["totals"]["kids"], 0)
        self.assertEqual(payload["activity"]["notes"]["items"], [])
        self.assertEqual(payload["activity"]["transactions"]["items"], [])
