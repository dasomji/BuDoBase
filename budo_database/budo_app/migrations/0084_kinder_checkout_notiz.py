from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0083_kid_edit_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="kinder",
            name="checkout_notiz",
            field=models.TextField(blank=True, default=""),
        ),
    ]
