from django.db import migrations, models


def install_monotonic_activation(apps, schema_editor):
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


def remove_monotonic_activation(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        table = apps.get_model("budo_app", "Profil")._meta.db_table
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS budo_profile_activation_monotonic ON {table}"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS budo_profile_activation_monotonic()")
    elif vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS budo_profile_activation_monotonic")


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0094_security_audit_event")]

    operations = [
        migrations.AlterField(
            model_name="profil",
            name="membership_selection_enabled",
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.RunPython(
            install_monotonic_activation, remove_monotonic_activation,
        ),
    ]
