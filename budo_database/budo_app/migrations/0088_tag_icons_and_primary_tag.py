from django.db import migrations, models
import django.db.models.deletion


def initialize_primary_tags(apps, schema_editor):
    Auslagerorte = apps.get_model("budo_app", "Auslagerorte")
    for place in Auslagerorte.objects.prefetch_related("tags").all():
        tag = min(
            place.tags.all(),
            key=lambda item: (item.name.casefold(), item.id),
            default=None,
        )
        if tag is not None:
            place.primary_tag_id = tag.id
            place.save(update_fields=["primary_tag"])


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0087_auslagerorte_travel_times")]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="icon",
            field=models.CharField(
                choices=[
                    ("map-pin", "Ort"),
                    ("tent-tree", "Zeltplatz"),
                    ("house", "Haus"),
                    ("warehouse", "Halle"),
                    ("trees", "Wald"),
                    ("mountain", "Berg"),
                    ("waves", "Wasser"),
                    ("castle", "Burg"),
                    ("utensils", "Essen"),
                    ("bed", "Übernachtung"),
                    ("bus", "Bus"),
                    ("accessibility", "Barrierefrei"),
                ],
                default="map-pin",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="auslagerorte",
            name="primary_tag",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="primary_for_auslagerorte",
                to="budo_app.tag",
            ),
        ),
        migrations.RunPython(initialize_primary_tags, migrations.RunPython.noop),
    ]
