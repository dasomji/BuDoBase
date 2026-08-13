from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Kinder, Turnus


class TurnusSwitchContractTests(TestCase):
    def test_user_switches_between_only_their_approved_turnusse(self):
        first = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        second = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 15),
        )
        foreign = Turnus.objects.create(
            turnus_nr=3,
            turnus_beginn=date(2026, 8, 1),
        )
        user = User.objects.create_user(username="switcher", password="secret")
        create_membership(user=user, turnus=first)
        create_membership(user=user, turnus=second)
        select_turnus(user, first)
        Kinder.objects.create(
            kid_index="T1-1",
            kid_vorname="First",
            kid_nachname="Child",
            turnus=first,
        )
        second_child = Kinder.objects.create(
            kid_index="T2-1",
            kid_vorname="Second",
            kid_nachname="Child",
            turnus=second,
        )
        Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Foreign",
            kid_nachname="Child",
            turnus=foreign,
        )
        self.client.force_login(user)

        bootstrap = self.client.get(reverse("bootstrap-api"))

        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(
            bootstrap.json()["turnus_selection"],
            {
                "selected_id": first.id,
                "options": [
                    {"id": first.id, "label": str(first)},
                    {"id": second.id, "label": str(second)},
                ],
            },
        )

        switched = self.client.post(
            "/api/turnus-selection/",
            {"turnus_id": second.id},
            content_type="application/json",
        )
        dashboard = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "dashboard"})
        )

        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.json(), {"selected_id": second.id})
        self.assertEqual(
            [kid["id"] for kid in dashboard.json()["kids"]],
            [second_child.id],
        )

        forged = self.client.post(
            "/api/turnus-selection/",
            {"turnus_id": foreign.id},
            content_type="application/json",
        )

        self.assertEqual(forged.status_code, 403)
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["turnus_selection"][
                "selected_id"
            ],
            second.id,
        )
