from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.models import Turnus, TurnusMembership


class LeitungTeamManagementHttpTests(TestCase):
    def test_leitung_can_add_an_available_account_as_teamer_to_own_turnus(self):
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2027, 7, 10),
        )
        leitung = User.objects.create_user("leitung")
        available = User.objects.create_user(
            "alex",
            first_name="Alex",
            last_name="Muster",
        )
        TurnusMembership.objects.create(
            user=leitung,
            turnus=turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        self.client.force_login(leitung)

        response = self.client.post(
            f"/api/turnusse/{turnus.id}/memberships/",
            {"user_id": available.id},
        )

        self.assertEqual(response.status_code, 201)
        workspace = self.client.get(
            reverse("route-data-api", args=("team-management",))
        )
        self.assertEqual(workspace.status_code, 200)
        managed_turnus = workspace.json()["years"][0]["turnuses"][0]
        self.assertEqual(
            managed_turnus["members"],
            [
                {
                    "id": managed_turnus["members"][0]["id"],
                    "user_id": leitung.id,
                    "name": "leitung",
                    "functional_role": "leitung",
                    "role_label": "Leitung",
                    "team_label": "",
                },
                {
                    "id": response.json()["membership_id"],
                    "user_id": available.id,
                    "name": "Alex Muster",
                    "functional_role": "teamer",
                    "role_label": "Teamer",
                    "team_label": "",
                },
            ],
        )
