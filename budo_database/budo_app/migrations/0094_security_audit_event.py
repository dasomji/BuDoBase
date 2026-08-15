from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0093_profil_membership_selection_enabled")]

    operations = [
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
    ]
