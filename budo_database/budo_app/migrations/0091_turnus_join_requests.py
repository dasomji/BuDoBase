from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0090_turnus_memberships"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TurnusJoinRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Ausstehend"), ("approved", "Angenommen"), ("rejected", "Abgelehnt"), ("cancelled", "Storniert"), ("superseded", "Ersetzt")], default="pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("turnus", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="join_requests", to="budo_app.turnus")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="turnus_join_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddConstraint(
            model_name="turnusjoinrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "pending")), fields=("user", "turnus"), name="unique_pending_user_turnus_join_request"),
        ),
    ]
