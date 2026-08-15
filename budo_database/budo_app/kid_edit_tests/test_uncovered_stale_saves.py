import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import Kinder, Turnus
from budo_app.test_membership_fixtures import approve_and_select_turnus


class UncoveredStaleSaveTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=16108,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="final-repair-writer",
            password="secret",
        )
        approve_and_select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.child = Kinder.objects.create(
            kid_index="SYNTHETIC-FINAL-REPAIR",
            kid_vorname="Stale covered",
            kid_nachname="Child",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            illness="Stale condition",
            zug_abreise=False,
            notiz_abreise="",
            anwesend=True,
            e_card=True,
            ausweis=True,
        )

    def stale_child_with_fresh_covered_state(self):
        stale_child = Kinder.objects.get(pk=self.child.pk)
        Kinder.objects.filter(pk=self.child.pk).update(
            kid_vorname="Fresh covered",
            illness="Fresh condition",
            edit_version=7,
        )
        return stale_child

    def assert_fresh_covered_state(self):
        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Fresh covered")
        self.assertEqual(self.child.illness, "Fresh condition")
        self.assertEqual(self.child.edit_version, 7)

    def test_deposit_preserves_fresher_covered_state_and_response(self):
        stale_child = self.stale_child_with_fresh_covered_state()

        with patch(
            "budo_app.views.get_active_kid_or_404",
            return_value=stale_child,
        ):
            response = self.client.post(
                reverse("update_pfand"),
                data=json.dumps({
                    "id": self.child.pk,
                    "action": "increase",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "success",
            "new_pfand": 1,
            "remaining_taschengeld": -0.25,
        })
        self.assert_fresh_covered_state()
        self.assertEqual(self.child.pfand, 1)

    def test_departure_toggle_preserves_fresher_covered_state_and_response(self):
        stale_child = self.stale_child_with_fresh_covered_state()

        with patch(
            "budo_app.kids_views.get_active_kid_or_404",
            return_value=stale_child,
        ):
            response = self.client.post(
                reverse("toggle_zug_abreise"),
                {"id": self.child.pk},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "success",
            "new_count": 1,
        })
        self.assert_fresh_covered_state()
        self.assertIs(self.child.zug_abreise, True)

    def test_departure_note_preserves_fresher_covered_state_and_response(self):
        stale_child = self.stale_child_with_fresh_covered_state()

        with patch(
            "budo_app.kids_views.get_active_kid_or_404",
            return_value=stale_child,
        ):
            response = self.client.post(
                reverse("update_notiz_abreise"),
                data=json.dumps({
                    "id": self.child.pk,
                    "notiz_abreise": "Synthetic departure point",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})
        self.assert_fresh_covered_state()
        self.assertEqual(
            self.child.notiz_abreise,
            "Synthetic departure point",
        )

    def test_checkout_preserves_fresher_covered_state_and_redirect(self):
        stale_child = self.stale_child_with_fresh_covered_state()

        with patch(
            "budo_app.kids_views.get_active_kid_or_404",
            return_value=stale_child,
        ):
            response = self.client.post(
                reverse("check_out", args=(self.child.pk,)),
                {
                    "early_abreise_date": "2026-07-05",
                    "notiz": "",
                    "amount": "",
                },
            )

        self.assertRedirects(
            response,
            reverse("kid_details", args=(self.child.pk,)),
        )
        self.assert_fresh_covered_state()
        self.assertEqual(
            self.child.early_abreise_date,
            date(2026, 7, 5),
        )
        self.assertIs(self.child.anwesend, False)
        self.assertIs(self.child.e_card, False)
        self.assertIs(self.child.ausweis, False)
