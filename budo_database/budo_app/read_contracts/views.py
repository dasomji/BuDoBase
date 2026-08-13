from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction

from budo_app.audit_policy import AuditAwareIsAuthenticated
from budo_app.memberships import lock_selected_membership_for_read

from .registry import get_contract


@api_view(["GET"])
@permission_classes([AuditAwareIsAuthenticated])
@transaction.atomic
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
    membership = lock_selected_membership_for_read(request.user)
    request.active_turnus = membership.turnus if membership is not None else None
    request.selected_profile = (
        membership.user.profil if membership is not None else None
    )
    response = Response(contract.builder(request))
    if contract.cache_control is not None:
        response["Cache-Control"] = contract.cache_control
    return response
