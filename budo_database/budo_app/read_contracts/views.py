from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry import get_contract


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def route_data(request, contract_key):
    """Dispatch an authenticated route read without falling back to app-data."""
    contract = get_contract(contract_key)
    if contract is None:
        return Response(
            {
                "code": "unknown_contract",
                "detail": "Unknown route contract.",
            },
            status=404,
        )
    if contract.builder is None:
        return Response(
            {
                "code": "contract_not_implemented",
                "contract": contract.key,
                "detail": "Route contract is not available yet.",
            },
            status=404,
        )
    return Response(contract.builder(request))
