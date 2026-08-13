from django.db import migrations, models


def mark_existing_selection(apps, schema_editor):
    Profil = apps.get_model("budo_app", "Profil")
    Profil.objects.filter(selected_turnus__isnull=False).update(
        membership_selection_enabled=True
    )


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0092_turnus_join_request_notifications")]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="membership_selection_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="SecurityAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.BigIntegerField(blank=True, null=True)),
                ("action", models.CharField(max_length=100)),
                ("reason", models.CharField(max_length=40)),
                ("request_id", models.CharField(max_length=255)),
                ("attempted_turnus_id", models.BigIntegerField(blank=True, null=True)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-occurred_at", "-id")},
        ),
        migrations.AddIndex(
            model_name="securityauditevent",
            index=models.Index(fields=["action", "-occurred_at"], name="security_audit_action_idx"),
        ),
        migrations.RunPython(mark_existing_selection, migrations.RunPython.noop),
    ]
