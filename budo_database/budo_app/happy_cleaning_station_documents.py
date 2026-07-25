"""Restricted, framework-independent operations for Happy Cleaning documents."""

from copy import deepcopy

from django.core.exceptions import ValidationError


def empty_station_document():
    return {"type": "doc", "content": []}


class StationDocumentConflict(ValueError):
    def __init__(self, current_version):
        super().__init__("stale task version")
        self.current_version = current_version


def _require_keys(node, allowed):
    if not isinstance(node, dict) or set(node) - allowed:
        raise ValidationError("Malformed station document node.")


def _validate_text(node):
    _require_keys(node, {"type", "text"})
    if node.get("type") != "text" or not isinstance(node.get("text"), str):
        raise ValidationError("Malformed text node.")


def _validate_paragraph(node):
    _require_keys(node, {"type", "content"})
    if node.get("type") != "paragraph":
        raise ValidationError("Only paragraphs are allowed here.")
    content = node.get("content", [])
    if not isinstance(content, list):
        raise ValidationError("Paragraph content must be a list.")
    for child in content:
        _validate_text(child)


def _validate_task_item(node, identities):
    _require_keys(node, {"type", "attrs", "content"})
    attrs = node.get("attrs")
    if node.get("type") != "taskItem" or not isinstance(attrs, dict):
        raise ValidationError("Malformed task item.")
    _require_keys(attrs, {"id", "checked", "version"})
    identity = attrs.get("id")
    version = attrs.get("version")
    if (
        isinstance(identity, bool)
        or not isinstance(identity, int)
        or identity <= 0
        or identity in identities
        or not isinstance(attrs.get("checked"), bool)
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version <= 0
    ):
        raise ValidationError("Task identity, checked state, or version is invalid.")
    identities.add(identity)
    content = node.get("content")
    if not isinstance(content, list) or len(content) != 1:
        raise ValidationError("A task item must contain one paragraph.")
    _validate_paragraph(content[0])


def validate_station_document(document):
    _require_keys(document, {"type", "content"})
    if document.get("type") != "doc":
        raise ValidationError("The station document must be a TipTap doc.")
    content = document.get("content")
    if not isinstance(content, list):
        raise ValidationError("Document content must be a list.")
    identities = set()
    for node in content:
        if not isinstance(node, dict):
            raise ValidationError("Malformed station document node.")
        if node.get("type") == "paragraph":
            _validate_paragraph(node)
        elif node.get("type") == "taskList":
            _require_keys(node, {"type", "content"})
            tasks = node.get("content")
            if not isinstance(tasks, list):
                raise ValidationError("Task-list content must be a list.")
            for task in tasks:
                _validate_task_item(task, identities)
        else:
            raise ValidationError("Unsupported station document node.")


def validate_structural_edit_document(document):
    """Validate the small TipTap schema accepted before server IDs are assigned."""
    _require_keys(document, {"type", "content"})
    if document.get("type") != "doc" or not isinstance(document.get("content"), list):
        raise ValidationError("The station document must be a TipTap doc.")
    identities = set()
    for node in document["content"]:
        if not isinstance(node, dict):
            raise ValidationError("Malformed station document node.")
        if node.get("type") == "paragraph":
            _validate_paragraph(node)
            continue
        if node.get("type") != "taskList":
            raise ValidationError("Unsupported station document node.")
        _require_keys(node, {"type", "content"})
        if not isinstance(node.get("content"), list):
            raise ValidationError("Task-list content must be a list.")
        for task in node["content"]:
            _require_keys(task, {"type", "attrs", "content"})
            attrs = task.get("attrs")
            if task.get("type") != "taskItem" or not isinstance(attrs, dict):
                raise ValidationError("Malformed task item.")
            _require_keys(attrs, {"id", "checked", "version"})
            identity = attrs.get("id")
            if identity is not None and (
                isinstance(identity, bool)
                or not isinstance(identity, int)
                or identity <= 0
                or identity in identities
            ):
                raise ValidationError("Task identity is invalid.")
            if identity is not None:
                identities.add(identity)
            if attrs.get("checked") is not None and not isinstance(attrs["checked"], bool):
                raise ValidationError("Task checked state is invalid.")
            version = attrs.get("version")
            if version is not None and (
                isinstance(version, bool) or not isinstance(version, int) or version <= 0
            ):
                raise ValidationError("Task version is invalid.")
            content = task.get("content")
            if not isinstance(content, list) or len(content) != 1:
                raise ValidationError("A task item must contain one paragraph.")
            _validate_paragraph(content[0])


def _paragraph(text):
    content = [] if not text else [{"type": "text", "text": text}]
    return {"type": "paragraph", "content": content}


def document_from_todos(todos):
    tasks = [{
        "type": "taskItem",
        "attrs": {
            "id": todo["id"],
            "checked": todo["checked"],
            "version": todo["version"],
        },
        "content": [_paragraph(todo["text"])],
    } for todo in todos]
    document = empty_station_document()
    if tasks:
        document["content"].append({"type": "taskList", "content": tasks})
    validate_station_document(document)
    return document


def _task_nodes(document):
    validate_station_document(document)
    for node in document["content"]:
        if node["type"] == "taskList":
            yield from node["content"]


def _task_text(task):
    return "".join(
        node["text"] for node in task["content"][0].get("content", [])
    )


def project_tasks(document):
    return [{
        "id": task["attrs"]["id"],
        "text": _task_text(task),
        "checked": task["attrs"]["checked"],
        "version": task["attrs"]["version"],
    } for task in _task_nodes(document)]


def count_tasks(document):
    tasks = list(_task_nodes(document))
    return {
        "total": len(tasks),
        "checked": sum(task["attrs"]["checked"] for task in tasks),
    }


def find_task(document, identity):
    return next(
        (task for task in _task_nodes(document) if task["attrs"]["id"] == identity),
        None,
    )


def mutate_task(
    document,
    identity,
    *,
    expected_version,
    checked=None,
    text=None,
):
    changed = deepcopy(document)
    task = find_task(changed, identity)
    if task is None:
        raise KeyError(identity)
    if task["attrs"]["version"] != expected_version:
        raise StationDocumentConflict(task["attrs"]["version"])
    if checked is not None:
        if not isinstance(checked, bool):
            raise ValidationError("Checked state must be boolean.")
        task["attrs"]["checked"] = checked
    if text is not None:
        if not isinstance(text, str):
            raise ValidationError("Task text must be text.")
        task["content"] = [_paragraph(text)]
    task["attrs"]["version"] += 1
    validate_station_document(changed)
    return changed
