from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("budo_app", "0085_extend_auslagerorte_maps_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
            ],
            options={"ordering": ("name", "id")},
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(
                Lower("name"),
                name="unique_tag_name_case_insensitive",
            ),
        ),
        migrations.AddField(
            model_name="auslagerorte",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                related_name="auslagerorte",
                to="budo_app.tag",
            ),
        ),
    ]
