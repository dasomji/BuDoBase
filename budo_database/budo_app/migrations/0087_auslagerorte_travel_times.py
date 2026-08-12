from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0086_tag_auslagerorte_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="auslagerorte",
            name="driving_minutes",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="auslagerorte",
            name="walking_minutes",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
