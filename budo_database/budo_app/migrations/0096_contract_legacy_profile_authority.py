from django.db import migrations


LEGACY_TEAM_LABELS = {
    "b": "Betreuer:in",
    "k": "Küche",
    "o": "Organisator",
    "f": "Freiwillige:r",
    "": "",
}


def reconcile_late_legacy_authority(apps, schema_editor):
    """Capture profile writes made after the expand migration was deployed."""
    Profil = apps.get_model("budo_app", "Profil")
    Membership = apps.get_model("budo_app", "TurnusMembership")
    for profile in Profil.objects.filter(
        membership_selection_enabled=False,
    ).exclude(turnus_id=None).iterator():
        legacy_label = LEGACY_TEAM_LABELS.get(profile.rolle, "")
        Membership.objects.get_or_create(
            user_id=profile.user_id,
            turnus_id=profile.turnus_id,
            defaults={"functional_role": "teamer", "team_label": legacy_label},
        )
        if profile.selected_turnus_id != profile.turnus_id:
            profile.selected_turnus_id = profile.turnus_id
            profile.save(update_fields=("selected_turnus",))


def restore_legacy_authority(apps, schema_editor):
    Profil = apps.get_model("budo_app", "Profil")
    Membership = apps.get_model("budo_app", "TurnusMembership")
    reverse_labels = {label: code for code, label in LEGACY_TEAM_LABELS.items()}
    for profile in Profil.objects.exclude(selected_turnus_id=None).iterator():
        membership = Membership.objects.filter(
            user_id=profile.user_id, turnus_id=profile.selected_turnus_id
        ).first()
        if membership is None:
            continue
        profile.turnus_id = profile.selected_turnus_id
        profile.rolle = reverse_labels.get(membership.team_label, "")
        profile.membership_selection_enabled = True
        profile.save(update_fields=("turnus", "rolle", "membership_selection_enabled"))


class Migration(migrations.Migration):
    # This data-only migration must commit before 0097 alters Profil. PostgreSQL
    # rejects ALTER TABLE while these updates still have pending trigger events.
    dependencies = [("budo_app", "0095_harden_membership_selection_activation")]

    operations = [
        migrations.RunPython(
            reconcile_late_legacy_authority,
            restore_legacy_authority,
        ),
    ]
