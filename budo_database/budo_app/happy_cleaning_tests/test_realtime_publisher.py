import os
import asyncio
from pathlib import Path
import subprocess
import sys
from unittest import skipUnless
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from budo_app.happy_cleaning_assignment_publisher import (
    build_invalidation_envelope,
    publish_assignment_invalidation_on_commit,
    reset_assignment_publisher,
)


class HappyCleaningInvalidationEnvelopeTests(SimpleTestCase):
    def test_envelope_is_versioned_and_contains_only_allow_listed_metadata(self):
        envelope = build_invalidation_envelope({
            "kind": "assignment",
            "happy_cleaning_id": 7,
            "revision": 12,
            "request_id": "assign-12",
            "child_id": 99,
            "private_payload": "secret",
        })

        self.assertEqual(set(envelope), {
            "version",
            "event_id",
            "projection",
            "revision",
            "invalidation_id",
            "request_id",
        })
        self.assertEqual(envelope["version"], 1)
        self.assertEqual(envelope["event_id"], 7)
        self.assertEqual(envelope["projection"], "assignments")
        self.assertEqual(envelope["revision"], 12)
        self.assertEqual(envelope["request_id"], "assign-12")


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
})
class HappyCleaningPostCommitDeliveryTests(TransactionTestCase):
    def tearDown(self):
        reset_assignment_publisher()

    def test_commit_delivers_once_and_rollback_delivers_nothing(self):
        layer = get_channel_layer()

        async def subscribe():
            channel = await layer.new_channel()
            await layer.group_add("happy_cleaning.event.7", channel)
            return channel

        channel = async_to_sync(subscribe)()
        payload = {
            "kind": "assignment",
            "happy_cleaning_id": 7,
            "revision": 5,
            "request_id": "assign-5",
        }
        with transaction.atomic():
            publish_assignment_invalidation_on_commit(payload)
        delivered = async_to_sync(layer.receive)(channel)
        self.assertEqual(delivered["envelope"]["revision"], 5)

        try:
            with transaction.atomic():
                publish_assignment_invalidation_on_commit({**payload, "revision": 6})
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

        async def receives_nothing():
            try:
                await asyncio.wait_for(layer.receive(channel), timeout=0.05)
            except asyncio.TimeoutError:
                return True
            return False

        self.assertTrue(async_to_sync(receives_nothing)())


class HappyCleaningProductionSettingsTests(SimpleTestCase):
    def _production_import(self, redis_url=None):
        project_root = Path(__file__).resolve().parents[2]
        environment = {
            **os.environ,
            "DJANGO_ENVIRONMENT": "production",
            "DJANGO_SECRET_KEY": "test-secret",
            "APP_URL": "example.test",
            "DATABASE_URL": "postgresql://user:pass@db.invalid/database",
            "S3_BUCKET_NAME": "bucket",
            "S3_ACCESS_KEY_ID": "key",
            "S3_SECRET_ACCESS_KEY": "secret",
            "S3_REGION_NAME": "auto",
            "S3_ENDPOINT_URL": "https://s3.invalid",
        }
        if redis_url is None:
            environment["REDIS_URL"] = ""
        else:
            environment["REDIS_URL"] = redis_url
        return subprocess.run(
            [sys.executable, "-c", "import budo_database.settings"],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_production_requires_a_valid_redis_url(self):
        missing = self._production_import()
        invalid = self._production_import("https://redis.invalid")
        valid = self._production_import("rediss://redis.example.test:6380/0")

        self.assertIn("REDIS_URL must be set", missing.stderr)
        self.assertIn("valid redis:// or rediss://", invalid.stderr)
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_deployment_uses_the_asgi_entrypoint(self):
        project_root = Path(__file__).resolve().parents[2]
        self.assertIn("daphne", (project_root / "Procfile").read_text())
        self.assertIn(
            "budo_database.asgi:application",
            (project_root / "railway.json").read_text(),
        )


@skipUnless(os.environ.get("REDIS_URL"), "REDIS_URL integration service is required")
class RedisChannelLayerIntegrationTests(SimpleTestCase):
    def test_separate_layer_instances_exchange_an_invalidation(self):
        from channels_redis.core import RedisChannelLayer

        async def scenario():
            prefix = f"budobase-test-{uuid4().hex}"
            sender = RedisChannelLayer(hosts=[os.environ["REDIS_URL"]], prefix=prefix)
            receiver = RedisChannelLayer(hosts=[os.environ["REDIS_URL"]], prefix=prefix)
            channel = await receiver.new_channel()
            await receiver.group_add("happy_cleaning.event.7", channel)
            await sender.group_send("happy_cleaning.event.7", {
                "type": "happy_cleaning.invalidation",
                "envelope": {"revision": 9},
            })
            event = await receiver.receive(channel)
            await sender.close_pools()
            await receiver.close_pools()
            return event

        event = async_to_sync(scenario)()
        self.assertEqual(event["envelope"]["revision"], 9)
