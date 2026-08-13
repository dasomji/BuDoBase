"""Public domain operations for approved Turnus memberships and selection."""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Profil, Turnus, TurnusMembership


@transaction.atomic
def select_turnus(user, turnus):
    """Select an approved Turnus, without treating selection as authority."""
    if not TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
        raise ValidationError("Der ausgewählte Turnus erfordert eine Mitgliedschaft.")

    profile = Profil.objects.select_for_update().get(user=user)
    profile.selected_turnus = turnus
    profile.save(update_fields=("selected_turnus",))
    return turnus


def selected_turnus_for(user):
    """Return selected Turnus only while an approved membership exists."""
    if not getattr(user, "is_authenticated", False):
        return None

    turnus_id = (
        Profil.objects.filter(user=user)
        .values_list("selected_turnus_id", flat=True)
        .first()
    )
    if turnus_id is None:
        return None
    if not TurnusMembership.objects.filter(
        user=user, turnus_id=turnus_id
    ).exists():
        return None
    return Turnus.objects.filter(pk=turnus_id).first()
