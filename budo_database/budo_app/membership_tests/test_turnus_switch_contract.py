from datetime import date
from threading import Event, Thread
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import AuditEvent, Kinder, Profil, Turnus


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

    def test_revoked_selection_falls_back_to_an_approved_membership_and_persists(self):
        first = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        second = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 7, 15))
        user = User.objects.create_user(username="fallback")
        first_membership = create_membership(user=user, turnus=first)
        create_membership(user=user, turnus=second)
        select_turnus(user, first)
        first_membership.delete()
        self.client.force_login(user)

        selection = self.client.get(reverse("bootstrap-api")).json()["turnus_selection"]

        self.assertEqual(selection["selected_id"], second.id)
        self.assertEqual(selection["options"], [{"id": second.id, "label": str(second)}])
        self.assertEqual(Profil.objects.get(user=user).selected_turnus_id, second.id)

    def test_successful_switch_is_audited_without_personal_details(self):
        first = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        second = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 7, 15))
        user = User.objects.create_user(username="audited", email="private@example.test")
        create_membership(user=user, turnus=first)
        create_membership(user=user, turnus=second)
        select_turnus(user, first)
        self.client.force_login(user)

        response = self.client.post(
            reverse("turnus-selection-api"),
            {"turnus_id": second.id},
            content_type="application/json",
            HTTP_X_REQUEST_ID="switch-request",
        )

        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(action="turnus.selection.switch")
        self.assertEqual(event.turnus, second)
        self.assertEqual(event.details, {
            "previous_turnus_id": first.id,
            "selected_turnus_id": second.id,
        })
        self.assertNotIn(user.email, str(event.details))

    def test_forged_and_stale_switches_are_audited_in_current_scope(self):
        current = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        forbidden = Turnus.objects.create(turnus_nr=2, turnus_beginn=date(2026, 7, 15))
        user = User.objects.create_user(username="rejected", email="secret@example.test")
        create_membership(user=user, turnus=current)
        select_turnus(user, current)
        self.client.force_login(user)

        for requested_id in (forbidden.id, 999999, "not-an-id"):
            response = self.client.post(
                reverse("turnus-selection-api"),
                {"turnus_id": requested_id},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400 if isinstance(requested_id, str) else 403)

        events = AuditEvent.objects.filter(action="turnus.selection.switch")
        self.assertEqual(events.count(), 3)
        self.assertEqual({event.turnus_id for event in events}, {current.id})
        self.assertEqual({event.outcome for event in events}, {"forbidden"})
        self.assertEqual(
            {event.details["selected_turnus_id"] for event in events},
            {current.id, forbidden.id, 999999},
        )
        self.assertNotIn(user.email, str([event.details for event in events]))


@skipUnlessDBFeature("has_select_for_update")
class TurnusSelectionConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_dashboard_reads_finish_before_concurrent_membership_removal(self):
        turnus = Turnus.objects.create(turnus_nr=1, turnus_beginn=date(2026, 7, 1))
        user = User.objects.create_user(username="concurrent", password="secret")
        membership = create_membership(user=user, turnus=turnus)
        select_turnus(user, turnus)
        Kinder.objects.create(
            kid_index="race-1", kid_vorname="Still", kid_nachname="Authorized",
            turnus=turnus,
        )
        reader_started = Event()
        allow_reader_to_finish = Event()
        deletion_finished = Event()
        result = {}
        from budo_app.read_contracts.domains.dashboard import _empty_summary

        def pause_after_authorization(profile):
            reader_started.set()
            self.assertTrue(allow_reader_to_finish.wait(5))
            return _empty_summary(profile)

        def read_dashboard():
            close_old_connections()
            client = Client()
            client.force_login(User.objects.get(pk=user.pk))
            with patch(
                "budo_app.read_contracts.domains.dashboard._empty_summary",
                side_effect=pause_after_authorization,
            ):
                response = client.get(
                    reverse("route-data-api", kwargs={"contract_key": "dashboard"})
                )
            result["status"] = response.status_code
            result["kid_ids"] = [kid["id"] for kid in response.json()["kids"]]
            close_old_connections()

        def remove_membership():
            close_old_connections()
            membership.__class__.objects.filter(pk=membership.pk).delete()
            deletion_finished.set()
            close_old_connections()

        reader = Thread(target=read_dashboard)
        reader.start()
        self.assertTrue(reader_started.wait(5))
        remover = Thread(target=remove_membership)
        remover.start()
        self.assertFalse(deletion_finished.wait(0.2))
        allow_reader_to_finish.set()
        reader.join(5)
        remover.join(5)

        self.assertEqual(result["status"], 200)
        self.assertEqual(result["kid_ids"], list(Kinder.objects.values_list("id", flat=True)))
        self.assertTrue(deletion_finished.is_set())
