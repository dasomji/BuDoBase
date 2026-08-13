from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import AuditEventData, actor_label_for_user, client_ip_from_request, record_audit_event
from .memberships import create_membership, update_membership
from .models import Turnus, TurnusMembership
from .product_admin_policy import require_product_admin
from .react_views import render_react_page
from .turnus_selection_views import _positive_bigint


@require_GET
def team_management_page(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    if not request.user.is_superuser and not request.user.turnus_memberships.filter(
        functional_role=TurnusMembership.FunctionalRole.LEITUNG
    ).exists():
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Team management access denied.")
    return render_react_page(request)


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_leitung_membership(request, turnus_id):
    require_product_admin(request.user, "Admin team management access denied.")
    user_id = _positive_bigint(request.data.get("user_id"))
    if user_id is None:
        raise ValidationError({"user_id": "Eine gültige Person ist erforderlich."})
    with transaction.atomic():
        turnus = get_object_or_404(Turnus, pk=turnus_id)
        user = get_object_or_404(get_user_model(), pk=user_id, is_active=True)
        if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
            raise ValidationError({"detail": "Diese Person gehört bereits zu diesem Turnus."})
        try:
            membership = create_membership(
                user=user,
                turnus=turnus,
                functional_role=TurnusMembership.FunctionalRole.LEITUNG,
                team_label="",
            )
        except DjangoValidationError as error:
            if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
                raise ValidationError({"detail": "Diese Person gehört bereits zu diesem Turnus."}) from error
            raise ValidationError(error.message_dict) from error
        record_audit_event(AuditEventData(
            turnus=turnus,
            actor_id=request.user.pk,
            actor_label=actor_label_for_user(request.user),
            action="membership.create",
            outcome="success",
            resource_type="turnus_membership",
            resource_id=str(membership.pk),
            resource_label=str(membership),
            request_id=request.headers.get("X-Request-ID", f"membership-create-{membership.pk}"),
            client_ip=client_ip_from_request(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"functional_role": "leitung", "member_id": user.pk},
        ))
    return Response({
        "membership_id": membership.pk,
        "user_id": user.pk,
        "functional_role": membership.functional_role,
        "role_label": membership.get_functional_role_display(),
        "team_label": membership.team_label,
    }, status=201)
