from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0072_happycleaningcommandrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="kinder",
            name="happy_cleaning_number_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddConstraint(
            model_name="kinder",
            constraint=models.CheckConstraint(
                condition=models.Q(happy_cleaning_number_version__gt=0),
                name="kinder_hc_number_version_positive",
            ),
        ),
    ]
