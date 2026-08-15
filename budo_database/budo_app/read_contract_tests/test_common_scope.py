from datetime import date

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from budo_app.models import Profil, Turnus, TurnusMembership
from budo_app.read_contracts.common import active_turnus_id


User = get_user_model()


class ActiveTurnusIdTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.turnus = Turnus.objects.create(
            turnus_nr=1, turnus_beginn=date(2026, 7, 1)
        )

    def request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_resolver_requires_an_approved_membership(self):
        user = User.objects.create_user("no-authority")
        profile = Profil.objects.get(user=user)
        profile.selected_turnus = self.turnus
        profile.save(update_fields=("selected_turnus",))
        self.assertIsNone(active_turnus_id(self.request_for(user)))
        self.assertIsNone(Profil.objects.get(user=user).selected_turnus_id)

    def test_resolver_accepts_an_approved_selected_membership(self):
        user = User.objects.create_user("member")
        profile = Profil.objects.get(user=user)
        profile.selected_turnus = self.turnus
        profile.save(update_fields=("selected_turnus",))
        TurnusMembership.objects.create(user=user, turnus=self.turnus)
        self.assertEqual(active_turnus_id(self.request_for(user)), self.turnus.pk)

    def test_injected_request_scope_does_not_query_legacy_profile_fields(self):
        user = User.objects.create_user("injected")
        request = self.request_for(user)
        request.active_turnus = self.turnus
        with self.assertNumQueries(0):
            self.assertEqual(active_turnus_id(request), self.turnus.pk)
