from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_memberships(apps, schema_editor):
    Profil = apps.get_model("budo_app", "Profil")
    TurnusMembership = apps.get_model("budo_app", "TurnusMembership")

    profiles = Profil.objects.exclude(turnus_id=None).iterator()
    for profile in profiles:
        TurnusMembership.objects.get_or_create(
            user_id=profile.user_id,
            turnus_id=profile.turnus_id,
            defaults={
                "functional_role": "teamer",
                "team_label": profile.rolle,
            },
        )
        profile.selected_turnus_id = profile.turnus_id
        profile.save(update_fields=("selected_turnus",))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("budo_app", "0089_alter_tag_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="selected_turnus",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="selected_by_profiles",
                to="budo_app.turnus",
            ),
        ),
        migrations.CreateModel(
            name="TurnusMembership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "functional_role",
                    models.CharField(
                        choices=[("leitung", "Leitung"), ("teamer", "Teamer")],
                        default="teamer",
                        max_length=10,
                    ),
                ),
                ("team_label", models.CharField(blank=True, default="", max_length=255)),
                (
                    "turnus",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="budo_app.turnus",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="turnus_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "turnus"),
                        name="unique_user_turnus_membership",
                    )
                ]
            },
        ),
        migrations.RunPython(backfill_memberships, migrations.RunPython.noop),
    ]
