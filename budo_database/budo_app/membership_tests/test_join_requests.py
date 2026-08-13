from datetime import date, timedelta
from io import StringIO
from threading import Event, Thread
from time import sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from budo_app.join_requests import CLAIM_LEASE, deliver_pending_join_request_notifications
from budo_app.memberships import create_membership, update_membership
from budo_app.memberships import lock_membership_scope as real_lock_membership_scope
from budo_app.models import (
    Turnus,
    TurnusJoinRequest,
    TurnusJoinRequestNotification,
    TurnusMembership,
)
from budo_app.test_membership_fixtures import approve_and_select_turnus


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

    def test_migrated_user_awaits_membership_after_last_membership_is_deleted(self):
        membership = create_membership(
            user=self.requester,
            turnus=self.turnus,
        )
        profile = self.requester.profil
        profile.selected_turnus = self.turnus
        profile.save(update_fields=["selected_turnus"])
        TurnusJoinRequest.objects.create(
            user=self.requester,
            turnus=self.turnus,
            status=TurnusJoinRequest.Status.REJECTED,
        )

        membership.delete()
        payload = self.client.get(
            reverse("route-data-api", args=["dashboard"])
        ).json()

        self.assertTrue(payload["membership_awaiting"])
        self.assertEqual(payload["kids"], [])
        self.assertEqual(payload["team"], [])
        self.assertEqual(payload["focuses"], [])
        self.assertEqual(payload["happy_cleanings"], [])
        self.assertEqual(payload["turnuses"], [{
            "id": self.turnus.id,
            "label": str(self.turnus),
            "number": 2,
            "start": "2027-07-10",
            "request_status": "rejected",
        }])

    def test_membership_created_without_selection_awaits_after_deletion(self):
        profile = self.requester.profil
        membership = create_membership(user=self.requester, turnus=self.turnus)

        profile.refresh_from_db()
        self.assertIsNone(profile.selected_turnus_id)

        membership.delete()
        payload = self.client.get(
            reverse("route-data-api", args=["dashboard"])
        ).json()

        self.assertTrue(payload["membership_awaiting"])
        self.assertEqual(payload["kids"], [])
        self.assertEqual(payload["team"], [])
        self.assertEqual(payload["focuses"], [])
        self.assertEqual(payload["happy_cleanings"], [])

    def test_profile_without_membership_awaits_approved_access(self):
        payload = self.client.get(
            reverse("route-data-api", args=["dashboard"])
        ).json()

        self.assertTrue(payload["membership_awaiting"])
        self.assertEqual(payload["kids"], [])
        self.assertEqual(payload["team"], [])

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
            "budo_app.join_requests.EmailMessage.send",
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

        with patch("budo_app.join_requests.EmailMessage.send", return_value=1) as retry_send:
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

    def test_existing_pending_is_returned_without_attempting_an_insert(self):
        existing = TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        with patch(
            "budo_app.join_requests.TurnusJoinRequest.objects.create",
            side_effect=IntegrityError("unrelated constraint"),
        ) as create:
            response = self.client.post(reverse("turnus-join-request-api", args=[self.turnus.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], existing.id)
        create.assert_not_called()

    def test_every_leitung_has_durable_state_even_with_blank_legacy_email(self):
        invalid = User.objects.create_user("leitung-invalid", "", "safe-password")
        TurnusMembership.objects.create(
            user=invalid,
            turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("turnus-join-request-api", args=[self.turnus.id]))

        failed = TurnusJoinRequestNotification.objects.get(recipient_user=invalid)
        self.assertEqual(failed.state, TurnusJoinRequestNotification.State.FAILED)
        self.assertIn("valid email", failed.last_error)
        self.assertEqual(TurnusJoinRequestNotification.objects.count(), 3)

        stderr = StringIO()
        call_command("deliver_join_request_notifications", stderr=stderr)
        self.assertIn(f"#{failed.id}", stderr.getvalue())
        self.assertIn("operator action", stderr.getvalue())

    def test_membership_creation_supersedes_pending_request_under_shared_lock(self):
        request = TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        create_membership(user=self.requester, turnus=self.turnus)
        request.refresh_from_db()
        self.assertEqual(request.status, TurnusJoinRequest.Status.SUPERSEDED)
        self.assertTrue(
            TurnusMembership.objects.filter(user=self.requester, turnus=self.turnus).exists()
        )

    def test_delivery_uses_stable_idempotency_headers(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("turnus-join-request-api", args=[self.turnus.id]))
        notification = TurnusJoinRequestNotification.objects.first()
        message = next(item for item in mail.outbox if item.to == [notification.recipient_email])
        self.assertEqual(
            message.extra_headers["X-Idempotency-Key"],
            f"turnus-join-request-notification-{notification.id}",
        )
        self.assertIn(
            f"turnus-join-request-notification-{notification.id}",
            message.extra_headers["Message-ID"],
        )

    def test_stale_claim_is_recovered_but_live_claim_is_not_sent(self):
        request = TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        stale = TurnusJoinRequestNotification.objects.create(
            join_request=request,
            recipient_user=self.leitung,
            recipient_email=self.leitung.email,
            state=TurnusJoinRequestNotification.State.SENDING,
            claimed_at=timezone.now() - timedelta(hours=1),
        )
        live_user = User.objects.get(username="leitung-2")
        live = TurnusJoinRequestNotification.objects.create(
            join_request=request,
            recipient_user=live_user,
            recipient_email=live_user.email,
            state=TurnusJoinRequestNotification.State.SENDING,
            claimed_at=timezone.now(),
        )
        deliver_pending_join_request_notifications()
        stale.refresh_from_db()
        live.refresh_from_db()
        self.assertEqual(stale.state, TurnusJoinRequestNotification.State.DELIVERED)
        self.assertEqual(stale.attempts, 1)
        self.assertEqual(live.state, TurnusJoinRequestNotification.State.SENDING)
        self.assertEqual(len(mail.outbox), 1)

    def test_expired_worker_cannot_acknowledge_a_newer_delivery_claim(self):
        request = TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        notification = TurnusJoinRequestNotification.objects.create(
            join_request=request,
            recipient_user=self.leitung,
            recipient_email=self.leitung.email,
        )

        def replace_claim(*args, **kwargs):
            notification.refresh_from_db()
            TurnusJoinRequestNotification.objects.filter(pk=notification.pk).update(
                state=TurnusJoinRequestNotification.State.SENDING,
                claimed_at=notification.claimed_at + CLAIM_LEASE,
            )
            return 1

        with patch("budo_app.join_requests.EmailMessage.send", side_effect=replace_claim):
            deliver_pending_join_request_notifications([notification.pk])

        notification.refresh_from_db()
        self.assertEqual(notification.state, TurnusJoinRequestNotification.State.SENDING)
        self.assertIsNotNone(notification.claimed_at)
        self.assertIsNone(notification.delivered_at)

    def test_expired_worker_cannot_release_a_newer_claim_after_send_failure(self):
        request = TurnusJoinRequest.objects.create(user=self.requester, turnus=self.turnus)
        notification = TurnusJoinRequestNotification.objects.create(
            join_request=request,
            recipient_user=self.leitung,
            recipient_email=self.leitung.email,
        )

        def replace_claim_then_fail(*args, **kwargs):
            notification.refresh_from_db()
            TurnusJoinRequestNotification.objects.filter(pk=notification.pk).update(
                state=TurnusJoinRequestNotification.State.SENDING,
                claimed_at=notification.claimed_at + timedelta(minutes=15),
            )
            raise RuntimeError("old worker failed")

        with patch(
            "budo_app.join_requests.EmailMessage.send",
            side_effect=replace_claim_then_fail,
        ):
            deliver_pending_join_request_notifications([notification.pk])

        notification.refresh_from_db()
        self.assertEqual(notification.state, TurnusJoinRequestNotification.State.SENDING)
        self.assertIsNotNone(notification.claimed_at)
        self.assertEqual(notification.last_error, "")

    def test_approved_member_can_discover_other_turnuses_without_data_leak(self):
        approve_and_select_turnus(self.requester, self.turnus)
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


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks")
class MembershipRequestConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_membership_and_request_writers_serialize_on_shared_scope(self):
        turnus = Turnus.objects.create(turnus_nr=8, turnus_beginn=date(2028, 7, 1))
        requester = User.objects.create_user("race-requester", "race@example.com")
        locked = Event()
        release = Event()
        outcomes = []

        def pausing_lock(*, user_id, turnus_id):
            real_lock_membership_scope(user_id=user_id, turnus_id=turnus_id)
            locked.set()
            release.wait(timeout=5)

        def request_worker():
            close_old_connections()
            from budo_app.join_requests import create_join_request

            with patch("budo_app.join_requests.lock_membership_scope", pausing_lock):
                outcomes.append(create_join_request(user=requester, turnus=turnus))
            close_old_connections()

        def membership_worker():
            close_old_connections()
            create_membership(user=requester, turnus=turnus)
            close_old_connections()

        request_thread = Thread(target=request_worker)
        request_thread.start()
        self.assertTrue(locked.wait(timeout=5))
        membership_thread = Thread(target=membership_worker)
        membership_thread.start()
        sleep(0.2)
        release.set()
        request_thread.join(timeout=5)
        membership_thread.join(timeout=5)

        self.assertFalse(request_thread.is_alive())
        self.assertFalse(membership_thread.is_alive())
        self.assertEqual(len(outcomes), 1)
        join_request = outcomes[0][0]
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TurnusJoinRequest.Status.SUPERSEDED)
        self.assertTrue(
            TurnusMembership.objects.filter(user=requester, turnus=turnus).exists()
        )

    def test_role_update_and_leitung_notification_snapshot_share_turnus_lock(self):
        turnus = Turnus.objects.create(turnus_nr=9, turnus_beginn=date(2028, 7, 15))
        requester = User.objects.create_user("snapshot-requester", "requester@example.com")
        leader = User.objects.create_user("new-leader", "leader@example.com")
        membership = create_membership(user=leader, turnus=turnus)
        locked = Event()
        release = Event()
        outcomes = []

        def pausing_lock(*, user_id, turnus_id):
            real_lock_membership_scope(user_id=user_id, turnus_id=turnus_id)
            locked.set()
            release.wait(timeout=5)

        def update_worker():
            close_old_connections()
            current = TurnusMembership.objects.get(pk=membership.pk)
            with patch("budo_app.memberships.lock_membership_scope", pausing_lock):
                update_membership(
                    current,
                    functional_role=TurnusMembership.FunctionalRole.LEITUNG,
                )
            close_old_connections()

        def request_worker():
            close_old_connections()
            from budo_app.join_requests import create_join_request

            outcomes.append(create_join_request(user=requester, turnus=turnus))
            close_old_connections()

        update_thread = Thread(target=update_worker)
        update_thread.start()
        self.assertTrue(locked.wait(timeout=5))
        request_thread = Thread(target=request_worker)
        request_thread.start()
        sleep(0.2)
        release.set()
        update_thread.join(timeout=5)
        request_thread.join(timeout=5)

        self.assertFalse(update_thread.is_alive())
        self.assertFalse(request_thread.is_alive())
        self.assertEqual(len(outcomes), 1)
        request = outcomes[0][0]
        self.assertTrue(
            request.notifications.filter(recipient_user=leader).exists()
        )
