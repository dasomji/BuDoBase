from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budo_app", "0081_remove_happy_cleaning_todo"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="happycleaningstation",
            name="hc_station_capacity_positive",
        ),
        migrations.AddConstraint(
            model_name="happycleaningstation",
            constraint=models.CheckConstraint(
                condition=models.Q(max_kids__gte=0),
                name="hc_station_capacity_nonnegative",
            ),
        ),
    ]
