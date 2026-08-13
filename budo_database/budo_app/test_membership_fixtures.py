"""Shared test setup for the transitional profile-to-membership migration."""

from budo_app.models import TurnusMembership


def approve_and_select_turnus(user, turnus):
    """Give a test user approved access and select that same Turnus."""
    TurnusMembership.objects.get_or_create(user=user, turnus=turnus)
    profile = user.profil
    profile.turnus = turnus
    profile.selected_turnus = turnus
    profile.membership_selection_enabled = True
    profile.save(update_fields=(
        "turnus",
        "selected_turnus",
        "membership_selection_enabled",
    ))
    return profile
