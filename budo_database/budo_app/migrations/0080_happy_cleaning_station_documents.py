from django.db import migrations, models

import budo_app.happy_cleaning_station_documents


def backfill_station_documents(apps, schema_editor):
    Station = apps.get_model("budo_app", "HappyCleaningStation")
    Todo = apps.get_model("budo_app", "HappyCleaningTodo")
    for station in Station.objects.all().iterator():
        todos = Todo.objects.filter(station_id=station.pk).order_by(
            "position", "id"
        ).values("id", "text", "checked", "version")
        station.content_document = (
            budo_app.happy_cleaning_station_documents.document_from_todos(todos)
        )
        station.save(update_fields=["content_document"])


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0079_happy_cleaning_excused_assignment")]

    operations = [
        migrations.AddField(
            model_name="happycleaningstation",
            name="content_document",
            field=models.JSONField(
                default=(
                    budo_app.happy_cleaning_station_documents
                    .empty_station_document
                ),
                validators=[
                    (
                        budo_app.happy_cleaning_station_documents
                        .validate_station_document
                    ),
                ],
            ),
        ),
        migrations.RunPython(
            backfill_station_documents,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
