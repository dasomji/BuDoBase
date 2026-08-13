from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
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
