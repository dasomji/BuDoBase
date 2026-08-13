from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Kinder, Turnus
from budo_app.read_contracts.registry import ROUTE_CONTRACTS


KNOWN_ROUTE_CONTRACT_KEYS = (
    "audit-events",
    "dashboard",
    "gut-zu-wissen",
    "profile",
    "team",
    "turnus-list",
    "turnus-upload",
    "admin-settings",
    "admin-team-overview",
    "team-management",
    "kids-directory",
    "train-departure",
    "train-arrival",
    "kid-detail",
    "kid-edit",
    "check-in",
    "check-out",
    "serial-letter",
    "murder-game",
    "focus-create",
    "focus-update",
    "focus-detail",
    "focus-meals",
    "focus-dashboard",
    "places-list",
    "place-create",
    "place-update",
    "place-images",
    "place-detail",
    "place-tag-settings",
    "kitchen",
    "allocation",
    "kid-count",
    "families",
    "special-upload",
    "special-families",
    "birthdays",
    "happy-cleaning-overview",
    "happy-cleaning-assignment",
    "happy-cleaning-overview-station",
    "happy-cleaning-print",
    "happy-cleaning-todo-print",
)

class RouteContractDispatchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="route-contract-user",
            password="secret",
        )

    def contract_url(self, key):
        return reverse("route-data-api", kwargs={"contract_key": key})

    def test_route_contracts_require_authentication(self):
        response = self.client.get(self.contract_url("dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_every_known_route_contract_has_a_builder(self):
        self.assertEqual(set(ROUTE_CONTRACTS), set(KNOWN_ROUTE_CONTRACT_KEYS))
        self.assertTrue(
            all(
                callable(contract.builder)
                for contract in ROUTE_CONTRACTS.values()
            )
        )

    def test_profile_contracts_use_glossary_aligned_domain_name(self):
        self.assertEqual(ROUTE_CONTRACTS["profile"].domain, "profiles")
        self.assertEqual(ROUTE_CONTRACTS["team"].domain, "profiles")

    def test_unknown_route_contract_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.get(self.contract_url("complete-application"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "code": "unknown_contract",
                "detail": "Unknown route contract.",
            },
        )

    def test_scoped_contracts_require_the_approved_selected_membership(self):
        legacy_turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        selected_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 15),
        )
        self.user.profil.turnus = legacy_turnus
        self.user.profil.save(update_fields=("turnus",))
        membership = create_membership(
            user=self.user,
            turnus=selected_turnus,
        )
        select_turnus(self.user, selected_turnus)
        Kinder.objects.create(
            kid_index="LEGACY-1",
            kid_vorname="Legacy",
            kid_nachname="Turnus",
            turnus=legacy_turnus,
        )
        Kinder.objects.create(
            kid_index="SELECTED-1",
            kid_vorname="Selected",
            kid_nachname="Member",
            turnus=selected_turnus,
        )
        self.client.force_login(self.user)

        selected_response = self.client.get(
            self.contract_url("kids-directory")
        )

        self.assertEqual(selected_response.status_code, 200)
        self.assertEqual(
            [kid["full_name"] for kid in selected_response.json()["kids"]],
            ["Selected Member"],
        )

        membership.delete()

        revoked_response = self.client.get(
            self.contract_url("kids-directory")
        )
        self.assertEqual(revoked_response.status_code, 404)
