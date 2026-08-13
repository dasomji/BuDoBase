from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import AuditEventData, actor_label_for_user, client_ip_from_request, record_audit_event
from .memberships import create_membership, lock_membership_scope, remove_membership, update_membership
from .models import Turnus, TurnusMembership
from .turnus_selection_views import _positive_bigint


def _can_manage_turnus(user, turnus_id):
    return user.is_superuser or TurnusMembership.objects.filter(
        user_id=user.pk,
        turnus_id=turnus_id,
        functional_role=TurnusMembership.FunctionalRole.LEITUNG,
    ).exists()


def _managed_turnus_or_404(user, turnus_id):
    queryset = Turnus.objects.all() if user.is_superuser else Turnus.objects.filter(
        memberships__user_id=user.pk,
        memberships__functional_role=TurnusMembership.FunctionalRole.LEITUNG,
    )
    return get_object_or_404(queryset, pk=turnus_id)


def _managed_membership_or_404(user, membership_id):
    queryset = TurnusMembership.objects.select_related("turnus", "user")
    if not user.is_superuser:
        queryset = queryset.filter(
            functional_role=TurnusMembership.FunctionalRole.TEAMER,
            turnus__memberships__user_id=user.pk,
            turnus__memberships__functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
    return get_object_or_404(queryset, pk=membership_id)


def _audit(request, *, membership, action, details):
    return record_audit_event(AuditEventData(
        turnus=membership.turnus,
        actor_id=request.user.pk,
        actor_label=actor_label_for_user(request.user),
        action=action,
        outcome="success",
        resource_type="turnus_membership",
        resource_id=str(membership.pk),
        resource_label=str(membership),
        request_id=request.headers.get("X-Request-ID", f"{action}-{membership.pk}"),
        client_ip=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        details=details,
    ))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_teamer_membership(request, turnus_id):
    user_id = _positive_bigint(request.data.get("user_id"))
    if user_id is None:
        raise ValidationError({"user_id": "Eine gültige Person ist erforderlich."})
    with transaction.atomic():
        turnus = _managed_turnus_or_404(request.user, turnus_id)
        # Lock the actor's authority for the lifetime of the mutation. Removal
        # follows the same parent-lock order and therefore cannot race this check.
        lock_membership_scope(user_id=request.user.pk, turnus_id=turnus.pk)
        if not _can_manage_turnus(request.user, turnus.pk):
            from django.http import Http404
            raise Http404
        user = get_object_or_404(get_user_model(), pk=user_id, is_active=True)
        if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
            raise ValidationError({"detail": "Diese Person gehört bereits zu diesem Turnus."})
        try:
            membership = create_membership(user=user, turnus=turnus)
        except DjangoValidationError as error:
            if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
                raise ValidationError({"detail": "Diese Person gehört bereits zu diesem Turnus."}) from error
            raise ValidationError(error.message_dict) from error
        _audit(request, membership=membership, action="membership.create", details={
            "functional_role": TurnusMembership.FunctionalRole.TEAMER,
            "member_id": user.pk,
        })
    return Response({
        "membership_id": membership.pk,
        "user_id": user.pk,
        "functional_role": membership.functional_role,
        "role_label": membership.get_functional_role_display(),
        "team_label": membership.team_label,
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_team_membership_label(request, membership_id):
    label = request.data.get("team_label")
    if not isinstance(label, str):
        raise ValidationError({"team_label": "Eine gültige Bezeichnung ist erforderlich."})
    label = label.strip()
    with transaction.atomic():
        membership = _managed_membership_or_404(request.user, membership_id)
        lock_membership_scope(user_id=request.user.pk, turnus_id=membership.turnus_id)
        if not _can_manage_turnus(request.user, membership.turnus_id):
            from django.http import Http404
            raise Http404
        previous = membership.team_label
        if previous != label:
            try:
                membership = update_membership(membership, team_label=label)
            except DjangoValidationError as error:
                raise ValidationError(error.message_dict) from error
            _audit(request, membership=membership, action="membership.label.change", details={
                "previous_label": previous, "new_label": label, "member_id": membership.user_id,
            })
    return Response({"membership_id": membership.pk, "team_label": label, "changed": previous != label})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_team_membership(request, membership_id):
    with transaction.atomic():
        membership = _managed_membership_or_404(request.user, membership_id)
        lock_membership_scope(user_id=request.user.pk, turnus_id=membership.turnus_id)
        if not _can_manage_turnus(request.user, membership.turnus_id):
            from django.http import Http404
            raise Http404
        snapshot = membership
        details = {"functional_role": membership.functional_role, "member_id": membership.user_id}
        # Audit before deletion preserves the canonical resource label, while
        # the outer transaction rolls both operations back together on failure.
        _audit(request, membership=snapshot, action="membership.remove", details=details)
        remove_membership(membership)
    return Response({"membership_id": membership_id, "removed": True})
