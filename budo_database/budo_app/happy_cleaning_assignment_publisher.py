"""Post-commit invalidation port for Happy Cleaning operational commands."""

from collections.abc import Callable
import logging
from typing import Any
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from budo_app.happy_cleaning_consumers import happy_cleaning_group_name


InvalidationPublisher = Callable[[dict[str, Any]], None]
logger = logging.getLogger(__name__)


def build_invalidation_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    projections = {
        "assignment": "assignments",
        "child_number": "child_numbers",
        "todo": "todos",
    }
    return {
        "version": 1,
        "event_id": payload["happy_cleaning_id"],
        "projection": projections[payload["kind"]],
        "revision": payload["revision"],
        "invalidation_id": str(uuid4()),
        "request_id": payload["request_id"],
    }


def publish_invalidation(payload: dict[str, Any]) -> None:
    envelope = build_invalidation_envelope(payload)
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Happy Cleaning invalidation skipped: no channel layer")
        return
    async_to_sync(channel_layer.group_send)(
        happy_cleaning_group_name(envelope["event_id"]),
        {
            "type": "happy_cleaning.invalidation",
            "envelope": envelope,
        },
    )


_publisher: InvalidationPublisher = publish_invalidation


def configure_assignment_publisher(publisher: InvalidationPublisher) -> None:
    global _publisher
    _publisher = publisher


def reset_assignment_publisher() -> None:
    global _publisher
    _publisher = publish_invalidation


def publish_assignment_invalidation_on_commit(payload: dict[str, Any]) -> None:
    committed_payload = dict(payload)
    transaction.on_commit(lambda: _publisher(committed_payload), robust=True)
