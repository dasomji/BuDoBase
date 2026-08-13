"""Shared test setup for approved membership selection."""

from budo_app.models import TurnusMembership


def approve_and_select_turnus(user, turnus):
    """Give a test user approved access and select that same Turnus."""
    TurnusMembership.objects.get_or_create(user=user, turnus=turnus)
    profile = user.profil
    profile.selected_turnus = turnus
    profile.save(update_fields=("selected_turnus",))
    return profile
