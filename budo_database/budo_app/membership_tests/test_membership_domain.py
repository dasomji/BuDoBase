from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from budo_app.memberships import (
    create_membership,
    selected_turnus_for,
    select_turnus,
    update_membership,
)
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
        create_membership(
            user=self.user,
            turnus=self.first,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
            team_label="Organisator",
        )
        create_membership(
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

        with self.assertRaises(ValidationError):
            create_membership(user=self.user, turnus=self.first)

    def test_selection_requires_membership_and_resolves_fail_closed(self):
        with self.assertRaises(ValidationError):
            select_turnus(self.user, self.first)

        membership = create_membership(user=self.user, turnus=self.first)
        select_turnus(self.user, self.first)
        self.assertEqual(selected_turnus_for(self.user), self.first)

        membership.delete()
        self.assertIsNone(selected_turnus_for(self.user))

    def test_team_label_does_not_change_functional_authority(self):
        membership = create_membership(
            user=self.user,
            turnus=self.first,
            functional_role=TurnusMembership.FunctionalRole.TEAMER,
            team_label="Leitung",
        )

        self.assertFalse(membership.is_leitung)

        update_membership(membership, team_label="Küche")
        membership.refresh_from_db()
        self.assertEqual(membership.team_label, "Küche")
        self.assertFalse(membership.is_leitung)

        update_membership(
            membership, functional_role=TurnusMembership.FunctionalRole.LEITUNG
        )
        membership.refresh_from_db()
        self.assertTrue(membership.is_leitung)

    def test_forged_selection_cannot_use_another_users_or_turnus_membership(self):
        other_user = User.objects.create_user(username="other-user")
        create_membership(user=other_user, turnus=self.first)
        create_membership(user=self.user, turnus=self.second)

        with self.assertRaises(ValidationError):
            select_turnus(self.user, self.first)

        select_turnus(self.user, self.second)
        self.assertEqual(selected_turnus_for(self.user), self.second)

    def test_profile_validation_and_resolution_share_approved_membership_rule(self):
        profile = self.user.profil
        profile.selected_turnus = self.first
        with self.assertRaises(ValidationError):
            profile.full_clean()

        membership = create_membership(user=self.user, turnus=self.first)
        profile.full_clean()
        profile.save(update_fields=("selected_turnus",))
        self.assertEqual(selected_turnus_for(self.user), self.first)

        membership.delete()
        self.assertIsNone(selected_turnus_for(self.user))
