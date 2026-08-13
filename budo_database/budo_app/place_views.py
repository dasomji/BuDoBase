from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Auslagerorte, AuslagerorteImage


def _require_permission(request, permission):
    if request.user.has_perm(permission):
        return None
    return Response(
        {"code": "permission_denied", "detail": "Keine Berechtigung."},
        status=403,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_place(request, place_id):
    denied = _require_permission(request, "budo_app.delete_auslagerorte")
    if denied:
        return denied
    place = get_object_or_404(Auslagerorte.objects.only("id", "name"), id=place_id)
    if request.data.get("confirmation_name") != place.name:
        return Response(
            {
                "code": "confirmation_mismatch",
                "detail": "Der eingegebene Name stimmt nicht exakt überein.",
            },
            status=400,
        )
    deleted = {"id": place.id, "name": place.name}
    place.delete()
    return Response({"deleted": deleted})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_place_image(request, place_id, image_id):
    denied = _require_permission(request, "budo_app.delete_auslagerorteimage")
    if denied:
        return denied
    image = get_object_or_404(
        AuslagerorteImage.objects.only("id", "auslagerort_id", "image"),
        id=image_id,
        auslagerort_id=place_id,
    )
    image.delete()
    return Response({"deleted": {"id": image_id}})
