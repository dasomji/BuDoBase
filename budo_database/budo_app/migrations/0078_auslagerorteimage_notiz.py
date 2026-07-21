from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0077_remove_schwerpunkte_geplante_abreise_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="auslagerorteimage",
            name="notiz",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="images",
                to="budo_app.auslagerortenotizen",
            ),
        ),
    ]
