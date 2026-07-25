from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HappyCleaningStationDocumentMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0079_happy_cleaning_excused_assignment")
    migrate_to = ("budo_app", "0080_happy_cleaning_station_documents")

    def test_forward_backfills_empty_and_ordered_mixed_legacy_todos(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        Turnus = apps.get_model("budo_app", "Turnus")
        Event = apps.get_model("budo_app", "HappyCleaning")
        Station = apps.get_model("budo_app", "HappyCleaningStation")
        Todo = apps.get_model("budo_app", "HappyCleaningTodo")
        turnus = Turnus.objects.create(
            turnus_nr=91, turnus_beginn=date(2026, 7, 1)
        )
        event = Event.objects.create(turnus=turnus, display_number=1)
        populated = Station.objects.create(
            happy_cleaning=event,
            name="Speisesaal",
            max_kids=3,
            meeting_point="Tür",
            position=1,
        )
        empty = Station.objects.create(
            happy_cleaning=event,
            name="Küche",
            max_kids=2,
            meeting_point="Tür",
            position=2,
        )
        second = Todo.objects.create(
            station=populated,
            text="Boden",
            position=2,
            checked=False,
            version=4,
        )
        first = Todo.objects.create(
            station=populated,
            text="Tische",
            position=1,
            checked=True,
            version=2,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        MigratedStation = migrated.get_model(
            "budo_app", "HappyCleaningStation"
        )

        self.assertEqual(
            MigratedStation.objects.get(pk=empty.pk).content_document,
            {"type": "doc", "content": []},
        )
        task_items = (
            MigratedStation.objects.get(pk=populated.pk)
            .content_document["content"][0]["content"]
        )
        self.assertEqual(
            [
                (
                    task["attrs"],
                    task["content"][0]["content"][0]["text"],
                )
                for task in task_items
            ],
            [
                ({"id": first.id, "checked": True, "version": 2}, "Tische"),
                ({"id": second.id, "checked": False, "version": 4}, "Boden"),
            ],
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        rolled_back = executor.loader.project_state([self.migrate_from]).apps
        self.assertEqual(
            rolled_back.get_model("budo_app", "HappyCleaningTodo").objects
            .filter(station_id=populated.pk)
            .count(),
            2,
        )

    def tearDown(self):
        MigrationExecutor(connection).migrate([
            ("budo_app", "0081_remove_happy_cleaning_todo")
        ])
        super().tearDown()
