from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from budo_app.join_requests import deliver_pending_join_request_notifications
from budo_app.models import (
    Turnus,
    TurnusJoinRequest,
    TurnusJoinRequestNotification,
    TurnusMembership,
)


class JoinRequestHttpTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2027, 7, 10))
        self.requester = User.objects.create_user(
            "requester", "requester@example.com", "safe-password"
        )
        self.leitung = User.objects.create_user(
            "leitung", "leitung@example.com", "safe-password"
        )
        TurnusMembership.objects.create(
            user=self.leitung,
            turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        second_leitung = User.objects.create_user(
            "leitung-2", "leitung-2@example.com", "safe-password"
        )
        TurnusMembership.objects.create(
            user=second_leitung,
            turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        self.client.force_login(self.requester)

    def test_request_is_pending_grants_no_access_and_notifies_leitung_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("turnus-join-request-api", args=[self.turnus.id])
            )

        self.assertEqual(response.status_code, 201)
        request = TurnusJoinRequest.objects.get(user=self.requester, turnus=self.turnus)
        self.assertEqual(request.status, TurnusJoinRequest.Status.PENDING)
        self.assertFalse(
            TurnusMembership.objects.filter(user=self.requester, turnus=self.turnus).exists()
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            {message.to[0] for message in mail.outbox},
            {"leitung@example.com", "leitung-2@example.com"},
        )
        for message in mail.outbox:
            self.assertIn("requester@example.com", message.body)
            self.assertIn(str(self.turnus), message.body)
            self.assertIn("unabhängigen Kanal", message.body)

        with self.captureOnCommitCallbacks(execute=True):
            duplicate = self.client.post(
                reverse("turnus-join-request-api", args=[self.turnus.id])
            )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(TurnusJoinRequest.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_awaiting_dashboard_contains_only_safe_request_state(self):
        TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        response = self.client.get(reverse("route-data-api", args=["dashboard"]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["membership_awaiting"])
        self.assertEqual(payload["kids"], [])
        self.assertEqual(payload["team"], [])
        self.assertEqual(payload["turnuses"], [{
                "id": self.turnus.id,
                "label": str(self.turnus),
                "number": 2,
                "start": "2027-07-10",
                "request_status": "pending",
            }])

    def test_anonymous_and_csrf_requests_are_rejected(self):
        self.client.logout()
        response = self.client.post(
            reverse("turnus-join-request-api", args=[self.turnus.id])
        )
        self.assertEqual(response.status_code, 302)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.requester)
        response = csrf_client.post(
            reverse("turnus-join-request-api", args=[self.turnus.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_failed_recipient_is_durable_and_retry_does_not_resend_successes(self):
        with patch(
            "budo_app.join_requests.send_mail",
            side_effect=[RuntimeError("backend unavailable"), 1],
        ) as mocked_send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("turnus-join-request-api", args=[self.turnus.id])
                )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mocked_send.call_count, 2)
        self.assertEqual(TurnusJoinRequestNotification.objects.count(), 2)
        self.assertEqual(
            TurnusJoinRequestNotification.objects.filter(delivered_at__isnull=True).count(),
            1,
        )

        with patch("budo_app.join_requests.send_mail", return_value=1) as retry_send:
            deliver_pending_join_request_notifications()
            deliver_pending_join_request_notifications()

        retry_send.assert_called_once()
        self.assertFalse(
            TurnusJoinRequestNotification.objects.filter(
                delivered_at__isnull=True
            ).exists()
        )

    def test_existing_membership_rejects_request_without_pending_or_email(self):
        TurnusMembership.objects.create(user=self.requester, turnus=self.turnus)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("turnus-join-request-api", args=[self.turnus.id])
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"code": "already_member"})
        self.assertFalse(TurnusJoinRequest.objects.filter(user=self.requester).exists())
        self.assertEqual(mail.outbox, [])

    def test_unrelated_integrity_error_is_not_misreported_as_duplicate(self):
        with patch(
            "budo_app.join_requests.TurnusJoinRequest.objects.create",
            side_effect=IntegrityError("unrelated constraint"),
        ):
            with self.assertRaises(IntegrityError):
                with self.captureOnCommitCallbacks(execute=True):
                    self.client.post(
                        reverse("turnus-join-request-api", args=[self.turnus.id])
                    )

    def test_approved_member_can_discover_other_turnuses_without_data_leak(self):
        TurnusMembership.objects.create(user=self.requester, turnus=self.turnus)
        profile = self.requester.profil
        profile.turnus = self.turnus
        profile.save(update_fields=["turnus"])
        other = Turnus.objects.create(turnus_nr=3, turnus_beginn=date(2027, 8, 1))

        payload = self.client.get(
            reverse("route-data-api", args=["dashboard"])
        ).json()

        self.assertNotIn("membership_awaiting", payload)
        self.assertEqual(
            payload["membership_turnuses"],
            [
                {
                    "id": other.id,
                    "label": str(other),
                    "number": 3,
                    "start": "2027-08-01",
                    "request_status": None,
                },
                {
                    "id": self.turnus.id,
                    "label": str(self.turnus),
                    "number": 2,
                    "start": "2027-07-10",
                    "request_status": "approved",
                },
            ],
        )
