from django.db import migrations


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
    # Keep trigger removal and all three column removals in one transaction so
    # a failed contraction leaves the complete legacy authority path intact.
    dependencies = [("budo_app", "0096_contract_legacy_profile_authority")]

    operations = [
        migrations.RunPython(remove_activation_guard, restore_activation_guard),
        migrations.RemoveField(model_name="profil", name="turnus"),
        migrations.RemoveField(model_name="profil", name="rolle"),
        migrations.RemoveField(
            model_name="profil", name="membership_selection_enabled"
        ),
    ]
