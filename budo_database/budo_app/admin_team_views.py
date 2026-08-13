from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import AuditEventData, actor_label_for_user, client_ip_from_request, record_audit_event
from .memberships import update_membership
from .models import TurnusMembership
from .product_admin_policy import require_product_admin
from .react_views import render_react_page


@require_GET
def admin_teams_page(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    require_product_admin(request.user, "Admin team management access denied.")
    return render_react_page(request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_membership_leadership(request, membership_id):
    require_product_admin(request.user, "Admin team management access denied.")
    role = request.data.get("functional_role")
    if role not in TurnusMembership.FunctionalRole.values:
        raise ValidationError({"functional_role": "Ungültige Funktionsrolle."})
    with transaction.atomic():
        membership = get_object_or_404(
            TurnusMembership.objects.select_for_update().select_related("turnus", "user"),
            pk=membership_id,
        )
        previous_role = membership.functional_role
        if previous_role == role:
            return Response({
                "membership_id": membership.pk,
                "functional_role": role,
                "changed": False,
            })
        try:
            membership = update_membership(membership, functional_role=role)
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict) from error
        record_audit_event(AuditEventData(
            turnus=membership.turnus,
            actor_id=request.user.pk,
            actor_label=actor_label_for_user(request.user),
            action="membership.role.change",
            outcome="success",
            resource_type="turnus_membership",
            resource_id=str(membership.pk),
            resource_label=str(membership),
            request_id=request.headers.get("X-Request-ID", f"membership-role-{membership.pk}"),
            client_ip=client_ip_from_request(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"previous_role": previous_role, "new_role": role, "member_id": membership.user_id},
        ))
    return Response({"membership_id": membership.pk, "functional_role": role, "changed": True})
