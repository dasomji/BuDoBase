from datetime import date
from threading import Barrier, Event, Thread
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from budo_app.join_requests import (
    JoinRequestAlreadyResolved,
    JoinRequestDecisionForbidden,
    decide_join_request,
)
from budo_app.memberships import lock_membership_scope
from budo_app.models import AuditEvent, Turnus, TurnusJoinRequest, TurnusMembership


class JoinRequestDecisionHttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2027, 7, 1))
        self.other_turnus = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2027, 7, 10))
        self.leitung = User.objects.create_user("lead")
        TurnusMembership.objects.create(
            user=self.leitung, turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )

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
        self.assertEqual(response.json()["approved_member"], {
            "id": response.json()["membership_id"],
            "user_id": requester.id,
            "name": "requester",
            "functional_role": TurnusMembership.FunctionalRole.TEAMER,
            "role_label": "Teamer",
            "team_label": "",
        })
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
        self.assertTrue(AuditEvent.objects.filter(
            action="join_request.approve",
            resource_id=str(join_request.id),
        ).exists())

    def test_decision_requires_csrf(self):
        requester = User.objects.create_user("csrf-requester")
        join_request = TurnusJoinRequest.objects.create(user=requester, turnus=self.turnus)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.leitung)

        response = client.post(
            reverse("join-request-decision-api", args=(join_request.id,)),
            {"decision": "approve"},
        )

        self.assertEqual(response.status_code, 403)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TurnusJoinRequest.Status.PENDING)

    def test_leitung_list_contains_only_pending_requests_for_led_turnusse(self):
        own_user = User.objects.create_user("own", email="own@example.test")
        other_user = User.objects.create_user("other")
        resolved_user = User.objects.create_user("resolved")
        own = TurnusJoinRequest.objects.create(user=own_user, turnus=self.turnus)
        TurnusJoinRequest.objects.create(user=other_user, turnus=self.other_turnus)
        TurnusJoinRequest.objects.create(
            user=resolved_user, turnus=self.turnus,
            status=TurnusJoinRequest.Status.REJECTED,
        )
        self.client.force_login(self.leitung)

        response = self.client.get(reverse("route-data-api", args=("team-management",)))

        self.assertEqual(response.status_code, 200)
        turnuses = [item for year in response.json()["years"] for item in year["turnuses"]]
        self.assertEqual(
            [item["id"] for item in turnuses],
            [self.other_turnus.id, self.turnus.id],
        )
        foreign = next(item for item in turnuses if item["id"] == self.other_turnus.id)
        managed = next(item for item in turnuses if item["id"] == self.turnus.id)
        self.assertFalse(foreign["can_view_team"])
        self.assertEqual(foreign["pending_requests"], [])
        self.assertEqual(managed["pending_requests"], [{
            "id": own.id, "user_id": own_user.id, "name": "Own", "email": "own@example.test",
        }])

    def test_admin_can_reject_across_turnusse_without_granting_access_and_it_is_audited(self):
        admin = User.objects.create_superuser("admin", "admin@example.test", "pw")
        requester = User.objects.create_user("requester")
        join_request = TurnusJoinRequest.objects.create(user=requester, turnus=self.other_turnus)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("join-request-decision-api", args=(join_request.id,)),
            {"decision": "reject"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "rejected")
        self.assertFalse(TurnusMembership.objects.filter(user=requester, turnus=self.other_turnus).exists())
        self.assertTrue(AuditEvent.objects.filter(action="join_request.reject", resource_id=str(join_request.id)).exists())

    def test_cross_turnus_decision_is_privacy_preserving_and_repeated_approval_is_safe(self):
        requester = User.objects.create_user("target")
        foreign = TurnusJoinRequest.objects.create(user=requester, turnus=self.other_turnus)
        self.client.force_login(self.leitung)
        url = reverse("join-request-decision-api", args=(foreign.id,))
        self.assertEqual(self.client.post(url, {"decision": "approve"}).status_code, 404)
        self.assertEqual(self.client.post(
            reverse("join-request-decision-api", args=(foreign.id + 9999,)),
            {"decision": "approve"},
        ).status_code, 404)
        self.assertFalse(TurnusMembership.objects.filter(user=requester).exists())

        own = TurnusJoinRequest.objects.create(user=requester, turnus=self.turnus)
        own_url = reverse("join-request-decision-api", args=(own.id,))
        self.assertEqual(self.client.post(own_url, {"decision": "approve"}).status_code, 200)
        self.assertEqual(self.client.post(own_url, {"decision": "approve"}).status_code, 400)
        self.assertEqual(TurnusMembership.objects.filter(user=requester, turnus=self.turnus).count(), 1)

    def test_audit_failure_rolls_back_request_and_membership(self):
        requester = User.objects.create_user("rollback")
        join_request = TurnusJoinRequest.objects.create(user=requester, turnus=self.turnus)
        self.client.force_login(self.leitung)
        with patch("budo_app.join_requests.record_audit_event", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("join-request-decision-api", args=(join_request.id,)),
                    {"decision": "approve"},
                )
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TurnusJoinRequest.Status.PENDING)
        self.assertFalse(TurnusMembership.objects.filter(user=requester, turnus=self.turnus).exists())


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks")
class JoinRequestDecisionConcurrencyTests(TransactionTestCase):
    def test_leitung_removed_while_decision_waits_cannot_approve(self):
        turnus = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2028, 6, 20))
        requester = User.objects.create_user("removed-lead-requester")
        leitung = User.objects.create_user("removed-lead")
        leadership = TurnusMembership.objects.create(
            user=leitung,
            turnus=turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        join_request = TurnusJoinRequest.objects.create(user=requester, turnus=turnus)
        removal_locked = Event()
        allow_removal = Event()
        decision_started = Event()
        outcome = []

        def remove_leitung():
            close_old_connections()
            with transaction.atomic():
                lock_membership_scope(user_id=leitung.id, turnus_id=turnus.id)
                TurnusMembership.objects.filter(pk=leadership.id).delete()
                removal_locked.set()
                allow_removal.wait(5)
            close_old_connections()

        def approve():
            close_old_connections()
            decision_started.set()
            try:
                decide_join_request(
                    join_request_id=join_request.id,
                    actor=User.objects.get(pk=leitung.id),
                    decision="approve",
                )
                outcome.append("approved")
            except JoinRequestDecisionForbidden:
                outcome.append("forbidden")
            finally:
                close_old_connections()

        remover = Thread(target=remove_leitung)
        remover.start()
        self.assertTrue(removal_locked.wait(5))
        decider = Thread(target=approve)
        decider.start()
        self.assertTrue(decision_started.wait(5))
        self.assertTrue(decider.is_alive())
        allow_removal.set()
        remover.join(10)
        decider.join(10)

        self.assertFalse(remover.is_alive())
        self.assertFalse(decider.is_alive())
        self.assertEqual(outcome, ["forbidden"])
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TurnusJoinRequest.Status.PENDING)
        self.assertFalse(
            TurnusMembership.objects.filter(user=requester, turnus=turnus).exists()
        )

    def test_concurrent_approvals_create_exactly_one_membership(self):
        turnus = Turnus.objects.create(turnus_nr=3, turnus_beginn=date(2028, 7, 1))
        requester = User.objects.create_user("race-requester")
        leitung = User.objects.create_user("race-leitung")
        TurnusMembership.objects.create(
            user=leitung,
            turnus=turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        join_request = TurnusJoinRequest.objects.create(user=requester, turnus=turnus)
        start = Barrier(2)
        outcomes = []

        def approve():
            close_old_connections()
            start.wait(timeout=5)
            try:
                decide_join_request(
                    join_request_id=join_request.id,
                    actor=User.objects.get(pk=leitung.id),
                    decision="approve",
                )
                outcomes.append("approved")
            except JoinRequestAlreadyResolved:
                outcomes.append("resolved")
            finally:
                close_old_connections()

        workers = [Thread(target=approve), Thread(target=approve)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)

        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertCountEqual(outcomes, ["approved", "resolved"])
        self.assertEqual(
            TurnusMembership.objects.filter(user=requester, turnus=turnus).count(),
            1,
        )
