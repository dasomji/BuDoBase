from django.db import migrations, models


def enable_existing_membership_profiles(apps, schema_editor):
    Profil = apps.get_model("budo_app", "Profil")
    TurnusMembership = apps.get_model("budo_app", "TurnusMembership")
    user_ids = TurnusMembership.objects.values_list("user_id", flat=True).distinct()
    Profil.objects.filter(user_id__in=user_ids).update(
        membership_selection_enabled=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0092_turnus_join_request_notifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="membership_selection_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            enable_existing_membership_profiles,
            migrations.RunPython.noop,
        ),
    ]
