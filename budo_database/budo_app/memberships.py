"""Public domain operations for approved Turnus memberships and selection."""

from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Profil, Turnus, TurnusJoinRequest, TurnusMembership


def _synchronize_cached_profile(user, profile):
    """Keep Django's reverse one-to-one cache from restoring stale authority."""
    cached = user._state.fields_cache.get("profil")
    if cached is not None:
        cached.turnus_id = profile.turnus_id
        cached.selected_turnus_id = profile.selected_turnus_id
        cached.membership_selection_enabled = profile.membership_selection_enabled


def lock_membership_scope(*, user_id, turnus_id):
    """Lock the stable parents used by all membership/request write workflows."""
    get_user_model().objects.select_for_update().get(pk=user_id)
    Turnus.objects.select_for_update().get(pk=turnus_id)
    Profil.objects.select_for_update().filter(user_id=user_id).first()


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
    profile = Profil.objects.get(user=user)
    profile.membership_selection_enabled = True
    profile.save(update_fields=("membership_selection_enabled",))
    _synchronize_cached_profile(user, profile)
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
    lock_membership_scope(user_id=user.pk, turnus_id=turnus.pk)
    profile = Profil.objects.select_for_update().get(user=user)
    membership = (
        approved_memberships_for(user)
        .select_for_update()
        .filter(turnus_id=turnus.pk)
        .first()
    )
    if membership is None:
        raise ValidationError("Der ausgewählte Turnus erfordert eine Mitgliedschaft.")
    profile.selected_turnus = turnus
    profile.membership_selection_enabled = True
    profile.save(update_fields=("selected_turnus", "membership_selection_enabled"))
    _synchronize_cached_profile(user, profile)
    return turnus


@transaction.atomic
def selected_turnus_for(user):
    """Return selected Turnus only while an approved membership exists."""
    if not getattr(user, "is_authenticated", False):
        return None

    profile = Profil.objects.select_for_update().filter(user=user).first()
    if profile is None:
        return None

    memberships = approved_memberships_for(user).select_for_update()
    membership = memberships.filter(turnus_id=profile.selected_turnus_id).first()
    if membership is not None:
        return membership.turnus

    # A missing or revoked selection must never remain an authority source.
    # Choose another approved membership deterministically, or clear the stale
    # value so callers enter the awaiting-membership experience.
    fallback_membership = (
        memberships
        .order_by("turnus__turnus_beginn", "turnus_id")
        .first()
    )
    fallback_id = (
        fallback_membership.turnus_id if fallback_membership is not None else None
    )
    profile.selected_turnus_id = fallback_id
    profile.save(update_fields=("selected_turnus",))
    _synchronize_cached_profile(user, profile)
    return fallback_membership.turnus if fallback_membership is not None else None


def scoped_turnus_for(user):
    """Resolve authority for a Turnus-scoped boundary during migration.

    Membership-enabled accounts always use the validated approved selection.
    The legacy branch exists only for profiles not activated by the expand
    migration and is removed with the profile authority field in #196.
    """
    if not getattr(user, "is_authenticated", False):
        return None
    profile = Profil.objects.select_related("turnus").filter(user=user).first()
    if profile is None:
        return None
    if profile.membership_selection_enabled:
        return selected_turnus_for(user)
    return profile.turnus


@contextmanager
def authorized_turnus_scope(user):
    """Hold the authority rows locked for the complete protected operation.

    Membership removal uses the same profile/user parent locking discipline as
    membership writes.  Consequently a removal can neither slip between an
    authorization check and its command nor invalidate a file snapshot while
    it is being opened.
    """
    with transaction.atomic():
        if not getattr(user, "is_authenticated", False):
            yield None
            return
        profile_snapshot = (
            Profil.objects.select_related("turnus").filter(user_id=user.pk).first()
        )
        if profile_snapshot is None:
            yield None
            return
        # Legacy-only profiles have no membership authority to protect.  Keep
        # their expand-phase read path at its established single-query cost;
        # #196 removes this branch with the legacy field.
        if not profile_snapshot.membership_selection_enabled:
            yield profile_snapshot.turnus
            return
        # Canonical order shared with membership writers.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        # The pre-lock read only establishes existence. Re-read after the User
        # lock because a selector may have committed while we waited for it.
        profile_snapshot = Profil.objects.filter(user_id=user.pk).values(
            "selected_turnus_id", "turnus_id", "membership_selection_enabled",
        ).get()
        turnus_id = (
            profile_snapshot["selected_turnus_id"]
            if profile_snapshot["membership_selection_enabled"]
            else profile_snapshot["turnus_id"]
        )
        if turnus_id is not None:
            Turnus.objects.select_for_update().filter(pk=turnus_id).first()
        profile = Profil.objects.select_for_update().get(user_id=user.pk)
        if not profile.membership_selection_enabled:
            yield None
            return
        membership = (
            TurnusMembership.objects.select_for_update()
            .select_related("turnus")
            .filter(user_id=user.pk, turnus_id=profile.selected_turnus_id)
            .first()
        )
        yield membership.turnus if membership is not None else None
