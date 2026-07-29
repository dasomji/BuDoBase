from copy import deepcopy

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from budo_app.happy_cleaning_station_documents import (
    count_tasks,
    document_from_todos,
    find_task,
    mutate_task,
    project_tasks,
    validate_station_document,
)


class HappyCleaningStationDocumentTests(SimpleTestCase):
    def setUp(self):
        self.document = document_from_todos([
            {"id": 11, "text": "Tische wischen", "checked": True, "version": 3},
            {"id": 12, "text": "Boden kehren", "checked": False, "version": 1},
        ])

    def test_projects_counts_and_finds_tasks_through_the_shared_api(self):
        validate_station_document(self.document)

        self.assertEqual(project_tasks(self.document), [
            {"id": 11, "text": "Tische wischen", "checked": True, "version": 3},
            {"id": 12, "text": "Boden kehren", "checked": False, "version": 1},
        ])
        self.assertEqual(count_tasks(self.document), {"total": 2, "checked": 1})
        self.assertEqual(find_task(self.document, 12)["attrs"]["version"], 1)

    def test_targeted_mutation_changes_only_the_selected_task_version(self):
        original = deepcopy(self.document)

        changed = mutate_task(
            self.document, 12, expected_version=1, checked=True
        )

        self.assertEqual(project_tasks(changed), [
            {"id": 11, "text": "Tische wischen", "checked": True, "version": 3},
            {"id": 12, "text": "Boden kehren", "checked": True, "version": 2},
        ])
        self.assertEqual(project_tasks(self.document), project_tasks(original))

    def test_rejects_nodes_attributes_and_invalid_task_metadata(self):
        malformed_documents = [
            {"type": "doc", "content": [{"type": "heading"}]},
            {"type": "doc", "secret": True, "content": []},
            {
                "type": "doc",
                "content": [{
                    "type": "taskList",
                    "content": [{
                        "type": "taskItem",
                        "attrs": {"id": 1, "checked": False, "version": 0},
                        "content": [{"type": "paragraph", "content": []}],
                    }],
                }],
            },
        ]

        for document in malformed_documents:
            with self.subTest(document=document), self.assertRaises(ValidationError):
                validate_station_document(document)
