from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .join_requests import (
    JoinRequestAlreadyResolved,
    JoinRequestDecisionForbidden,
    decide_join_request,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decide_turnus_join_request(request, join_request_id):
    decision = request.data.get("decision")
    if decision not in {"approve", "reject"}:
        raise ValidationError({"decision": "Bitte Anfrage annehmen oder ablehnen."})
    try:
        join_request, membership = decide_join_request(
            join_request_id=join_request_id,
            actor=request.user,
            decision=decision,
            http_request=request,
        )
    except JoinRequestDecisionForbidden as error:
        raise NotFound("Beitrittsanfrage nicht gefunden.") from error
    except JoinRequestAlreadyResolved as error:
        raise ValidationError({"detail": "Diese Beitrittsanfrage wurde bereits bearbeitet."}) from error
    return Response({
        "request_id": join_request.pk,
        "status": join_request.status,
        "membership_id": membership.pk if membership is not None else None,
    })
