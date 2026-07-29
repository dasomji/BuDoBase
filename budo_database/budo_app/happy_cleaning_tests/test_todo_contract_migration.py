from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from budo_app.happy_cleaning_tests.migration_fixtures import (
    restore_latest_migration_state,
)


class HappyCleaningTodoContractMigrationTests(TransactionTestCase):
    migrate_from = ("budo_app", "0080_happy_cleaning_station_documents")
    migrate_to = ("budo_app", "0081_remove_happy_cleaning_todo")

    def test_forward_preserves_representative_canonical_documents(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        Turnus = apps.get_model("budo_app", "Turnus")
        Event = apps.get_model("budo_app", "HappyCleaning")
        Station = apps.get_model("budo_app", "HappyCleaningStation")
        Todo = apps.get_model("budo_app", "HappyCleaningTodo")
        turnus = Turnus.objects.create(
            turnus_nr=86, turnus_beginn="2026-07-01"
        )
        event = Event.objects.create(turnus=turnus, display_number=1)
        documents = [
            {"type": "doc", "content": []},
            {
                "type": "doc",
                "content": [{
                    "type": "taskList",
                    "content": [
                        self.task(9, "Offen", False, 1),
                        self.task(4, "Erledigt", True, 3),
                    ],
                }],
            },
            {
                "type": "doc",
                "content": [
                    self.paragraph("Kopiert aus HC 1:"),
                    {"type": "taskList", "content": [
                        self.task(41, "Zusammengeführt", False, 2),
                    ]},
                    self.paragraph("Quelle: Turnus 4 / Station Bad"),
                ],
            },
        ]
        station_ids = [
            Station.objects.create(
                happy_cleaning=event,
                name=f"Station {position}",
                max_kids=2,
                meeting_point="Tür",
                position=position,
                content_document=deepcopy(document),
            ).id
            for position, document in enumerate(documents, start=1)
        ]
        for station_id, document in zip(station_ids, documents):
            tasks = [
                task
                for block in document["content"]
                if block["type"] == "taskList"
                for task in block["content"]
            ]
            for position, task in enumerate(tasks, start=1):
                Todo.objects.create(
                    id=task["attrs"]["id"],
                    station_id=station_id,
                    text="".join(
                        node["text"]
                        for node in task["content"][0]["content"]
                    ),
                    position=position,
                    checked=task["attrs"]["checked"],
                    version=task["attrs"]["version"],
                )

        mismatch = Todo.objects.get(pk=9)
        mismatch.text = "Nicht kanonisch"
        mismatch.save(update_fields=["text"])
        with self.assertRaisesMessage(
            ValidationError, "canonical tasks do not match legacy todo rows"
        ):
            MigrationExecutor(connection).migrate([self.migrate_to])
        mismatch.text = "Offen"
        mismatch.save(update_fields=["text"])

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated = executor.loader.project_state([self.migrate_to]).apps
        MigratedStation = migrated.get_model("budo_app", "HappyCleaningStation")

        self.assertEqual(
            [
                MigratedStation.objects.get(pk=station_id).content_document
                for station_id in station_ids
            ],
            documents,
        )
        with self.assertRaises(LookupError):
            migrated.get_model("budo_app", "HappyCleaningTodo")

    @staticmethod
    def paragraph(text):
        return {
            "type": "paragraph",
            "content": [{"type": "text", "text": text}],
        }

    @classmethod
    def task(cls, identity, text, checked, version):
        return {
            "type": "taskItem",
            "attrs": {
                "id": identity,
                "checked": checked,
                "version": version,
            },
            "content": [cls.paragraph(text)],
        }

    def tearDown(self):
        restore_latest_migration_state()
        super().tearDown()
