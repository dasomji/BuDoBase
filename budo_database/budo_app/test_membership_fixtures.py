"""Shared test setup for approved membership selection."""

from budo_app.models import TurnusMembership


def approve_and_select_turnus(user, turnus, *, team_label="", functional_role="teamer"):
    """Give a test user approved access and select that same Turnus."""
    membership, _ = TurnusMembership.objects.update_or_create(
        user=user,
        turnus=turnus,
        defaults={"team_label": team_label, "functional_role": functional_role},
    )
    profile = user.profil
    profile.selected_turnus = turnus
    profile.save()
    return profile
