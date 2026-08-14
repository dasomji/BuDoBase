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


def remove_activation_guard(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        table = apps.get_model("budo_app", "Profil")._meta.db_table
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS budo_profile_activation_monotonic ON {table}"
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS budo_profile_activation_monotonic()"
        )
    elif vendor == "sqlite":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS budo_profile_activation_monotonic"
        )
    else:
        raise RuntimeError(
            "Profile authority contraction supports only PostgreSQL and SQLite; "
            f"database vendor {vendor!r} requires an explicit trigger removal."
        )


def restore_activation_guard(apps, schema_editor):
    table = apps.get_model("budo_app", "Profil")._meta.db_table
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute(f"""
            CREATE FUNCTION budo_profile_activation_monotonic() RETURNS trigger AS $$
            BEGIN
                IF OLD.membership_selection_enabled AND NOT NEW.membership_selection_enabled THEN
                    RAISE EXCEPTION 'membership selection activation is irreversible';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        schema_editor.execute(f"""
            CREATE TRIGGER budo_profile_activation_monotonic
            BEFORE UPDATE ON {table} FOR EACH ROW
            EXECUTE FUNCTION budo_profile_activation_monotonic()
        """)
    elif vendor == "sqlite":
        schema_editor.execute(f"""
            CREATE TRIGGER budo_profile_activation_monotonic
            BEFORE UPDATE OF membership_selection_enabled ON {table}
            WHEN OLD.membership_selection_enabled = 1
                 AND NEW.membership_selection_enabled = 0
            BEGIN
                SELECT RAISE(ABORT, 'membership selection activation is irreversible');
            END;
        """)
    else:
        raise RuntimeError(
            "Profile authority contraction supports only PostgreSQL and SQLite; "
            f"database vendor {vendor!r} requires an explicit trigger restore."
        )


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0095_harden_membership_selection_activation")]

    operations = [
        migrations.RunPython(reconcile_late_legacy_authority, restore_legacy_authority),
        migrations.RunPython(remove_activation_guard, restore_activation_guard),
        migrations.RemoveField(model_name="profil", name="turnus"),
        migrations.RemoveField(model_name="profil", name="rolle"),
        migrations.RemoveField(
            model_name="profil", name="membership_selection_enabled"
        ),
    ]
