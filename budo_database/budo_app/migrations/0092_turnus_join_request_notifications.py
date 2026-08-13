import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0091_turnus_join_requests"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TurnusJoinRequestNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_email", models.EmailField(max_length=254)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True, default="")),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("join_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="budo_app.turnusjoinrequest")),
                ("recipient_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="join_request_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.AddConstraint(
            model_name="turnusjoinrequestnotification",
            constraint=models.UniqueConstraint(fields=("join_request", "recipient_user"), name="unique_join_request_notification_recipient"),
        ),
    ]
