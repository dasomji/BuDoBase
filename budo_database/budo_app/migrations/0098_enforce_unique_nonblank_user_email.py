from django.db import migrations
from django.db.models import Count
from django.db.models.functions import Lower


EMAIL_UNIQUE_INDEX_NAME = "auth_user_email_ci_unique"


def ensure_nonblank_emails_are_unique(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    duplicate_groups = (
        user_model.objects.using(schema_editor.connection.alias)
        .exclude(email="")
        .annotate(normalized_email=Lower("email"))
        .values("normalized_email")
        .annotate(user_count=Count("id"))
        .filter(user_count__gt=1)
    )
    if duplicate_groups.exists():
        raise RuntimeError(
            "Cannot enforce unique account emails while duplicate nonblank "
            "addresses exist. Clean duplicate emails case-insensitively, then "
            "run this migration again."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0097_remove_legacy_profile_authority"),
    ]

    operations = [
        migrations.RunPython(
            ensure_nonblank_emails_are_unique,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX "auth_user_email_ci_unique" '
                'ON "auth_user" (LOWER("email")) WHERE "email" <> \'\';'
            ),
            reverse_sql=(
                'DROP INDEX "auth_user_email_ci_unique";'
            ),
        ),
    ]
