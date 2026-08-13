from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from budo_app.models import Turnus, TurnusJoinRequest, TurnusMembership


class JoinRequestDecisionHttpTests(TestCase):
    def test_leitung_can_approve_request_for_own_turnus_as_one_teamer_membership(self):
        turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2027, 7, 10),
        )
        requester = User.objects.create_user("requester")
        leitung = User.objects.create_user("leitung")
        TurnusMembership.objects.create(
            user=leitung,
            turnus=turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        join_request = TurnusJoinRequest.objects.create(
            user=requester,
            turnus=turnus,
        )
        self.client.force_login(leitung)

        response = self.client.post(
            f"/api/join-requests/{join_request.pk}/decision/",
            {"decision": "approve"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], TurnusJoinRequest.Status.APPROVED)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TurnusJoinRequest.Status.APPROVED)
        memberships = TurnusMembership.objects.filter(
            user=requester,
            turnus=turnus,
        )
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(
            memberships.get().functional_role,
            TurnusMembership.FunctionalRole.TEAMER,
        )
