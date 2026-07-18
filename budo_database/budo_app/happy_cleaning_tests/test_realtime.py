from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from channels.security.websocket import OriginValidator
from channels.sessions import CookieMiddleware, SessionMiddleware
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from budo_app.happy_cleaning_consumers import (
    HappyCleaningInvalidationConsumer,
    may_access_happy_cleaning_event,
)
from budo_app.models import HappyCleaning, Turnus
from budo_database.asgi import application


class HappyCleaningSocketAuthorizationTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
        )
        self.user = User.objects.create_user(username="socket-operator")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))

    def test_only_the_users_active_turnus_and_a_live_immutable_event_are_allowed(self):
        self.assertTrue(may_access_happy_cleaning_event(self.user.id, self.event.id))
        self.assertFalse(may_access_happy_cleaning_event(
            self.user.id,
            self.other_event.id,
        ))
        stale_id = self.event.id
        self.event.delete()
        self.assertFalse(may_access_happy_cleaning_event(self.user.id, stale_id))


class HappyCleaningConsumerProtocolTests(SimpleTestCase):
    def _consumer(self, *, authenticated=True, allowed=True):
        consumer = HappyCleaningInvalidationConsumer()
        consumer.scope = {
            "user": SimpleNamespace(id=1, is_authenticated=authenticated),
            "url_route": {"kwargs": {"event_id": 7}},
        }
        consumer.channel_name = "test-channel"
        consumer.channel_layer = SimpleNamespace(
            group_add=AsyncMock(),
            group_discard=AsyncMock(),
        )
        consumer._may_access_event = AsyncMock(return_value=allowed)
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer.send_json = AsyncMock()
        return consumer

    def test_active_turnus_join_and_read_only_protocol(self):
        consumer = self._consumer()
        async_to_sync(consumer.connect)()

        consumer.channel_layer.group_add.assert_awaited_once_with(
            "happy_cleaning.event.7",
            "test-channel",
        )
        consumer.accept.assert_awaited_once()

        async_to_sync(consumer.receive_json)({"type": "assign", "child_id": 99})
        consumer.close.assert_awaited_once_with(code=4405)

    def test_anonymous_and_wrong_turnus_joins_are_rejected(self):
        anonymous = self._consumer(authenticated=False)
        wrong_turnus = self._consumer(allowed=False)

        async_to_sync(anonymous.connect)()
        async_to_sync(wrong_turnus.connect)()

        anonymous.close.assert_awaited_once_with(code=4401)
        wrong_turnus.close.assert_awaited_once_with(code=4404)
        anonymous.channel_layer.group_add.assert_not_awaited()
        wrong_turnus.channel_layer.group_add.assert_not_awaited()

    def test_only_allow_listed_envelope_fields_are_sent(self):
        consumer = self._consumer()
        envelope = {
            "version": 1,
            "event_id": 7,
            "projection": "todos",
            "revision": 9,
            "invalidation_id": "evt-9",
            "request_id": "todo-9",
        }
        async_to_sync(consumer.happy_cleaning_invalidation)({
            "envelope": envelope,
            "private_payload": "must not leak",
        })

        consumer.send_json.assert_awaited_once_with(envelope)

    def test_asgi_stack_applies_origin_validation_before_session_authentication(self):
        websocket = application.application_mapping["websocket"]
        self.assertIsInstance(websocket, OriginValidator)
        self.assertIsInstance(websocket.application, CookieMiddleware)
        self.assertIsInstance(websocket.application.inner, SessionMiddleware)
        self.assertNotIn("attacker.invalid", websocket.allowed_origins)
