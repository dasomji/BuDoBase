"""Authenticated read-only realtime invalidations for Happy Cleaning."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from budo_app.models import HappyCleaning, Profil


INVALIDATION_FIELDS = frozenset({
    "version",
    "event_id",
    "projection",
    "revision",
    "invalidation_id",
    "request_id",
})
PROJECTION_KINDS = frozenset({"assignments", "child_numbers", "todos"})


def happy_cleaning_group_name(event_id):
    return f"happy_cleaning.event.{event_id}"


def may_access_happy_cleaning_event(user_id, event_id):
    turnus_id = (
        Profil.objects.filter(user_id=user_id)
        .values_list("turnus_id", flat=True)
        .first()
    )
    if turnus_id is None:
        return False
    return HappyCleaning.objects.filter(
        pk=event_id,
        turnus_id=turnus_id,
    ).exists()


class HappyCleaningInvalidationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        event_id = self.scope["url_route"]["kwargs"]["event_id"]
        if not await self._may_access_event(user.id, event_id):
            await self.close(code=4404)
            return
        self.event_id = event_id
        self.group_name = happy_cleaning_group_name(event_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # HTTP commands are the sole mutation interface. Any client frame is a
        # protocol violation, not a command to interpret.
        await self.close(code=4405)

    async def happy_cleaning_invalidation(self, event):
        envelope = event.get("envelope", {})
        if self._valid_envelope(envelope):
            await self.send_json({key: envelope[key] for key in INVALIDATION_FIELDS})

    @staticmethod
    def _valid_envelope(envelope):
        return (
            isinstance(envelope, dict)
            and set(envelope) == INVALIDATION_FIELDS
            and envelope.get("version") == 1
            and isinstance(envelope.get("event_id"), int)
            and envelope.get("projection") in PROJECTION_KINDS
            and isinstance(envelope.get("revision"), int)
            and envelope.get("revision") >= 1
            and isinstance(envelope.get("invalidation_id"), str)
            and bool(envelope.get("invalidation_id"))
            and isinstance(envelope.get("request_id"), str)
            and bool(envelope.get("request_id"))
        )

    @database_sync_to_async
    def _may_access_event(self, user_id, event_id):
        return may_access_happy_cleaning_event(user_id, event_id)
