from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from budo_app.audit_policy import AuditAwareIsAuthenticated
from budo_app.audit_readiness import kid_edit_release_enabled

from .registry import get_contract
@api_view(["GET"])
@permission_classes([AuditAwareIsAuthenticated])
def route_data(request, contract_key):
    """Dispatch an authenticated route read without falling back to app-data."""
    if contract_key == "kid-edit" and not kid_edit_release_enabled():
        return Response(
            {"ok": False, "code": "release_gated"}, status=403,
        )
    contract = get_contract(contract_key)
    if contract is None:
        return Response(
            {
                "code": "unknown_contract",
                "detail": "Unknown route contract.",
            },
            status=404,
        )
    response = Response(contract.builder(request))
    if contract.cache_control is not None:
        response["Cache-Control"] = contract.cache_control
    return response
