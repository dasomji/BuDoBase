"""Public domain operations for approved Turnus memberships and selection."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Profil, Turnus, TurnusJoinRequest, TurnusMembership


def lock_membership_scope(*, user_id, turnus_id):
    """Lock the stable parents used by all membership/request write workflows."""
    get_user_model().objects.select_for_update().get(pk=user_id)
    Turnus.objects.select_for_update().get(pk=turnus_id)


def approved_memberships_for(user):
    """Return the sole authority-bearing membership query for ``user``."""
    if not getattr(user, "is_authenticated", False):
        return TurnusMembership.objects.none()
    return TurnusMembership.objects.filter(user=user)


def has_approved_membership(user, turnus):
    """Say whether ``user`` has approved access to exactly ``turnus``."""
    turnus_id = getattr(turnus, "pk", turnus)
    return approved_memberships_for(user).filter(turnus_id=turnus_id).exists()


@transaction.atomic
def create_membership(
    *,
    user,
    turnus,
    functional_role=TurnusMembership.FunctionalRole.TEAMER,
    team_label="",
):
    """Create one approved membership through the public domain seam."""
    lock_membership_scope(user_id=user.pk, turnus_id=turnus.pk)
    membership = TurnusMembership(
        user=user,
        turnus=turnus,
        functional_role=functional_role,
        team_label=team_label,
    )
    membership.full_clean()
    membership.save()
    TurnusJoinRequest.objects.filter(
        user=user,
        turnus=turnus,
        status=TurnusJoinRequest.Status.PENDING,
    ).update(status=TurnusJoinRequest.Status.SUPERSEDED)
    return membership


@transaction.atomic
def update_membership(membership, *, functional_role=None, team_label=None):
    """Change authority and/or its independent descriptive label explicitly."""
    lock_membership_scope(
        user_id=membership.user_id,
        turnus_id=membership.turnus_id,
    )
    membership = TurnusMembership.objects.select_for_update().get(pk=membership.pk)
    update_fields = []
    if functional_role is not None:
        membership.functional_role = functional_role
        update_fields.append("functional_role")
    if team_label is not None:
        membership.team_label = team_label
        update_fields.append("team_label")
    if not update_fields:
        return membership
    membership.full_clean()
    membership.save(update_fields=update_fields)
    return membership


@transaction.atomic
def select_turnus(user, turnus):
    """Select an approved Turnus, without treating selection as authority."""
    if not has_approved_membership(user, turnus):
        raise ValidationError("Der ausgewählte Turnus erfordert eine Mitgliedschaft.")

    profile = Profil.objects.select_for_update().get(user=user)
    profile.selected_turnus = turnus
    profile.save(update_fields=("selected_turnus",))
    return turnus


def selected_turnus_for(user):
    """Return selected Turnus only while an approved membership exists."""
    if not getattr(user, "is_authenticated", False):
        return None

    profile_values = (
        Profil.objects.filter(user=user)
        .values_list("selected_turnus_id", "turnus_id")
        .first()
    )
    if profile_values is None:
        return None
    turnus_id, legacy_turnus_id = profile_values
    if turnus_id is not None and has_approved_membership(user, turnus_id):
        return Turnus.objects.filter(pk=turnus_id).first()

    # A missing or revoked selection must never remain an authority source.
    # Choose another approved membership deterministically, or clear the stale
    # value so callers enter the awaiting-membership experience.
    fallback_id = (
        approved_memberships_for(user)
        .order_by("turnus__turnus_beginn", "turnus_id")
        .values_list("turnus_id", flat=True)
        .first()
    )
    Profil.objects.filter(user=user).update(selected_turnus_id=fallback_id)
    if fallback_id is None:
        # Expand-and-contract compatibility: callers whose legacy assignment
        # has not yet been converted continue to work. A stale explicit
        # selection never falls back to this field.
        if turnus_id is None and legacy_turnus_id is not None:
            return Turnus.objects.filter(pk=legacy_turnus_id).first()
        return None
    return Turnus.objects.filter(pk=fallback_id).first()
