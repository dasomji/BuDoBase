from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.read_contracts.registry import ROUTE_CONTRACTS


KNOWN_ROUTE_CONTRACT_KEYS = (
    "dashboard",
    "profile",
    "turnus-list",
    "turnus-upload",
    "kids-directory",
    "train-departure",
    "train-arrival",
    "kid-detail",
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
    "kitchen",
    "allocation",
    "kid-count",
    "families",
    "special-upload",
    "special-families",
    "birthdays",
    "teamer",
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
