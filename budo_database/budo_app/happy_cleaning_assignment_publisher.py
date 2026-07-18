"""Post-commit invalidation port for Happy Cleaning operational commands."""

from collections.abc import Callable
from typing import Any

from django.db import transaction


InvalidationPublisher = Callable[[dict[str, Any]], None]


def _discard_invalidation(payload: dict[str, Any]) -> None:
    """Default adapter: issue #41 will replace this inert implementation."""


_publisher: InvalidationPublisher = _discard_invalidation


def configure_assignment_publisher(publisher: InvalidationPublisher) -> None:
    global _publisher
    _publisher = publisher


def reset_assignment_publisher() -> None:
    global _publisher
    _publisher = _discard_invalidation


def publish_assignment_invalidation_on_commit(payload: dict[str, Any]) -> None:
    committed_payload = dict(payload)
    transaction.on_commit(lambda: _publisher(committed_payload))
