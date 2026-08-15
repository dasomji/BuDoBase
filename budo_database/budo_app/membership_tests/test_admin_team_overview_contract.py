from django.contrib.auth.models import User
from django.db import close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from datetime import date
from threading import Barrier, Event, Thread
from unittest import skipUnless
from unittest.mock import patch

from budo_app.memberships import lock_membership_scopes as real_lock_membership_scopes
from budo_app.models import Turnus, TurnusMembership


class AdminTeamOverviewAuthorizationTests(TestCase):
    def test_django_staff_without_superuser_authority_cannot_read_global_teams(self):
        staff_user = User.objects.create_user(
            username="django-staff-only",
            is_staff=True,
            is_superuser=False,
        )
        self.client.force_login(staff_user)

        response = self.client.get(
            reverse(
                "route-data-api",
                kwargs={"contract_key": "admin-team-overview"},
            )
        )

        self.assertEqual(response.status_code, 403)


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks")
class AdminMembershipWriterConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2028, 7, 10),
        )

    def test_admin_revocation_committed_before_actor_lock_blocks_role_change(self):
        admin = User.objects.create_superuser("revoked-admin", password="secret")
        target = User.objects.create_user("target")
        membership = TurnusMembership.objects.create(user=target, turnus=self.turnus)
        writer_reached_lock = Event()
        revocation_committed = Event()
        responses = []

        def delayed_lock(**kwargs):
            writer_reached_lock.set()
            self.assertTrue(revocation_committed.wait(5))
            return real_lock_membership_scopes(**kwargs)

        def write_role():
            close_old_connections()
            client = Client()
            client.force_login(User.objects.get(pk=admin.pk))
            with patch("budo_app.admin_team_views.lock_membership_scopes", delayed_lock):
                responses.append(client.post(
                    reverse("admin-membership-role-api", args=(membership.pk,)),
                    {"functional_role": TurnusMembership.FunctionalRole.LEITUNG},
                ).status_code)
            close_old_connections()

        writer = Thread(target=write_role)
        writer.start()
        self.assertTrue(writer_reached_lock.wait(5))
        User.objects.filter(pk=admin.pk).update(is_superuser=False)
        revocation_committed.set()
        writer.join(5)

        self.assertFalse(writer.is_alive())
        self.assertEqual(responses, [403])
        membership.refresh_from_db()
        self.assertEqual(membership.functional_role, TurnusMembership.FunctionalRole.TEAMER)

    def test_reciprocal_admin_target_writers_terminate_with_coherent_roles(self):
        first = User.objects.create_superuser("first-admin", password="secret")
        second = User.objects.create_superuser("second-admin", password="secret")
        first_membership = TurnusMembership.objects.create(
            user=first, turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        second_membership = TurnusMembership.objects.create(
            user=second, turnus=self.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        ready = Barrier(2)
        responses = []

        def aligned_lock(**kwargs):
            ready.wait(5)
            return real_lock_membership_scopes(**kwargs)

        def demote(actor_id, target_membership_id):
            close_old_connections()
            client = Client()
            client.force_login(User.objects.get(pk=actor_id))
            with patch("budo_app.admin_team_views.lock_membership_scopes", aligned_lock):
                responses.append(client.post(
                    reverse("admin-membership-role-api", args=(target_membership_id,)),
                    {"functional_role": TurnusMembership.FunctionalRole.TEAMER},
                ).status_code)
            close_old_connections()

        threads = [
            Thread(target=demote, args=(first.pk, second_membership.pk)),
            Thread(target=demote, args=(second.pk, first_membership.pk)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(responses), [200, 200])
        self.assertEqual(
            set(TurnusMembership.objects.filter(
                pk__in=(first_membership.pk, second_membership.pk),
            ).values_list("functional_role", flat=True)),
            {TurnusMembership.FunctionalRole.TEAMER},
        )
