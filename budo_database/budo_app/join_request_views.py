from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .join_requests import AlreadyTurnusMember, create_join_request
from .models import Turnus


@login_required
@require_POST
def request_turnus_membership(request, turnus_id):
    turnus = get_object_or_404(Turnus, pk=turnus_id)
    try:
        join_request, created = create_join_request(user=request.user, turnus=turnus)
    except AlreadyTurnusMember:
        return JsonResponse({"code": "already_member"}, status=409)
    return JsonResponse(
        {"id": join_request.id, "status": join_request.status},
        status=201 if created else 200,
    )
