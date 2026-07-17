from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


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

    def test_every_current_route_contract_is_known_but_not_exposed_yet(self):
        self.client.force_login(self.user)

        for key in KNOWN_ROUTE_CONTRACT_KEYS:
            with self.subTest(key=key):
                response = self.client.get(self.contract_url(key))

                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(),
                    {
                        "code": "contract_not_implemented",
                        "contract": key,
                        "detail": "Route contract is not available yet.",
                    },
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
