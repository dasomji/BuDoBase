from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes

from budo_app.audit_policy import AuditAwareIsAuthenticated
from budo_app.memberships import authorized_turnus_scope

from .registry import get_contract


@api_view(["GET"])
@permission_classes([AuditAwareIsAuthenticated])
def route_data(request, contract_key):
    """Dispatch an authenticated route read without falling back to app-data."""
    contract = get_contract(contract_key)
    if contract is None:
        return JsonResponse(
            {
                "code": "unknown_contract",
                "detail": "Unknown route contract.",
            },
            status=404,
        )
    with authorized_turnus_scope(request.user) as turnus:
        request.active_turnus = turnus
        response = JsonResponse(contract.builder(request))
        if contract.cache_control is not None:
            response["Cache-Control"] = contract.cache_control
        return response
