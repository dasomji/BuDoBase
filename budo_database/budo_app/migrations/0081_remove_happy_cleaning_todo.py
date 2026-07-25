from django.core.exceptions import ValidationError
from django.db import migrations


def require_canonical_station_documents(apps, schema_editor):
    from budo_app.happy_cleaning_station_documents import (
        project_tasks,
        validate_station_document,
    )

    Station = apps.get_model("budo_app", "HappyCleaningStation")
    Todo = apps.get_model("budo_app", "HappyCleaningTodo")
    for station in Station.objects.only("id", "content_document").iterator():
        try:
            validate_station_document(station.content_document)
        except ValidationError as error:
            raise ValidationError(
                f"Station {station.id} has no canonical content document: "
                f"{'; '.join(error.messages)}"
            ) from error
        canonical_tasks = project_tasks(station.content_document)
        legacy_tasks = list(
            Todo.objects.filter(station_id=station.id)
            .order_by("position", "id")
            .values("id", "text", "checked", "version")
        )
        if canonical_tasks != legacy_tasks:
            raise ValidationError(
                f"Station {station.id} canonical tasks do not match "
                "legacy todo rows; aborting destructive migration."
            )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [("budo_app", "0080_happy_cleaning_station_documents")]

    operations = [
        migrations.RunPython(
            require_canonical_station_documents,
            migrations.RunPython.noop,
        ),
        migrations.DeleteModel(name="HappyCleaningTodo"),
    ]
