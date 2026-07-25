"""Canonical-document task fixtures for Happy Cleaning behavior tests."""

from copy import deepcopy

from budo_app.happy_cleaning_station_documents import (
    document_from_todos,
    project_tasks,
    validate_station_document,
)
from budo_app.models import HappyCleaningStation


def document_with_tasks(document, tasks):
    changed = deepcopy(document)
    task_list = document_from_todos(tasks)["content"]
    first_task_list = next(
        (index for index, node in enumerate(changed["content"])
         if node["type"] == "taskList"),
        len(changed["content"]),
    )
    changed["content"] = [
        node for node in changed["content"] if node["type"] != "taskList"
    ]
    if task_list:
        changed["content"].insert(first_task_list, task_list[0])
    validate_station_document(changed)
    return changed


class CanonicalTask:
    objects = None

    def __init__(self, station, data):
        self.station = station
        self.station_id = station.id
        self._load(data)

    def _load(self, data):
        self.id = self.pk = data["id"]
        self.text = data["text"]
        self.checked = data["checked"]
        self.version = data["version"]
        self.position = data["position"]

    def refresh_from_db(self):
        self.station.refresh_from_db(fields=["content_document"])
        current = CanonicalTask.objects.get(pk=self.id)
        self._load(vars(current))

    def save(self, update_fields=None):
        tasks = project_tasks(self.station.content_document)
        for task in tasks:
            if task["id"] == self.id:
                task.update({
                    "text": self.text,
                    "checked": self.checked,
                    "version": self.version,
                })
        self.station.content_document = document_with_tasks(
            self.station.content_document, tasks,
        )
        self.station.save(update_fields=["content_document"])


class CanonicalTaskQuery:
    def __init__(self, station=None, pk=None, excluded_pk=None):
        self.station = station
        self.pk = pk
        self.excluded_pk = excluded_pk

    def _items(self):
        stations = (
            [self.station]
            if self.station is not None
            else HappyCleaningStation.objects.all()
        )
        result = []
        for station in stations:
            station.refresh_from_db(fields=["content_document"])
            for position, task in enumerate(
                project_tasks(station.content_document), start=1
            ):
                if self.pk is not None and task["id"] != self.pk:
                    continue
                if self.excluded_pk is not None and task["id"] == self.excluded_pk:
                    continue
                result.append(CanonicalTask(
                    station, {**task, "position": position},
                ))
        return result

    def count(self):
        return len(self._items())

    def get(self, **kwargs):
        query = self.filter(**kwargs) if kwargs else self
        items = query._items()
        if len(items) != 1:
            raise AssertionError(f"Expected one canonical task, got {len(items)}")
        return items[0]

    def first(self):
        items = self._items()
        return items[0] if items else None

    def exists(self):
        return bool(self._items())

    def filter(self, **kwargs):
        return CanonicalTaskQuery(
            station=kwargs.get("station", self.station),
            pk=kwargs.get("pk", kwargs.get("id", self.pk)),
            excluded_pk=self.excluded_pk,
        )

    def exclude(self, **kwargs):
        return CanonicalTaskQuery(
            station=self.station,
            pk=self.pk,
            excluded_pk=kwargs.get("pk", kwargs.get("id")),
        )

    def order_by(self, *_fields):
        return self

    def values_list(self, field, flat=False):
        values = [getattr(item, field) for item in self._items()]
        return values if flat else [(value,) for value in values]

    def update(self, **values):
        for item in self._items():
            for name, value in values.items():
                setattr(item, name, value)
            item.save()

    def create(self, *, station, text, position, checked=False, version=1):
        tasks = project_tasks(station.content_document)
        identity = max(
            (
                task["id"]
                for document in HappyCleaningStation.objects.values_list(
                    "content_document", flat=True
                )
                for task in project_tasks(document)
            ),
            default=0,
        ) + 1
        tasks.insert(position - 1, {
            "id": identity,
            "text": text,
            "checked": checked,
            "version": version,
        })
        station.content_document = document_with_tasks(
            station.content_document, tasks,
        )
        station.save(update_fields=["content_document"])
        return self.filter(station=station, pk=identity).get()

    def __iter__(self):
        return iter(self._items())


CanonicalTask.objects = CanonicalTaskQuery()
