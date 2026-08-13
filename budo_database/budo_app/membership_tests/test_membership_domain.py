from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from budo_app.memberships import selected_turnus_for, select_turnus
from budo_app.models import Turnus, TurnusMembership


class TurnusMembershipDomainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="multi-turnus")
        self.first = Turnus.objects.create(
            turnus_nr=1, turnus_beginn=date(2026, 7, 1)
        )
        self.second = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 15)
        )

    def test_account_can_have_one_membership_per_turnus_with_distinct_labels(self):
        TurnusMembership.objects.create(
            user=self.user,
            turnus=self.first,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
            team_label="Organisator",
        )
        TurnusMembership.objects.create(
            user=self.user,
            turnus=self.second,
            functional_role=TurnusMembership.FunctionalRole.TEAMER,
            team_label="Küche",
        )

        self.assertEqual(
            list(
                self.user.turnus_memberships.order_by("turnus_id").values_list(
                    "functional_role", "team_label"
                )
            ),
            [("leitung", "Organisator"), ("teamer", "Küche")],
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TurnusMembership.objects.create(user=self.user, turnus=self.first)

    def test_selection_requires_membership_and_resolves_fail_closed(self):
        with self.assertRaises(ValidationError):
            select_turnus(self.user, self.first)

        membership = TurnusMembership.objects.create(
            user=self.user, turnus=self.first
        )
        select_turnus(self.user, self.first)
        self.assertEqual(selected_turnus_for(self.user), self.first)

        membership.delete()
        self.assertIsNone(selected_turnus_for(self.user))

    def test_team_label_does_not_change_functional_authority(self):
        membership = TurnusMembership.objects.create(
            user=self.user,
            turnus=self.first,
            functional_role=TurnusMembership.FunctionalRole.TEAMER,
            team_label="Leitung",
        )

        self.assertFalse(membership.is_leitung)
