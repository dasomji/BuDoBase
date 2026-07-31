"""RED closure contract for audit retention and controlled read surfaces (#164-08)."""

from copy import deepcopy
from datetime import date

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from budo_app.audit_tests.test_kid_edit_audit_schema import valid_details
from budo_app.models import (
    AuditEvent,
    HappyCleaningCommandRequest,
    Kinder,
    Turnus,
)


class AuditClosureContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2, turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=3, turnus_beginn=date(2026, 8, 1),
        )
        self.actor = User.objects.create(username="retained-actor")
        self.child = Kinder.objects.create(
            turnus=self.turnus, kid_index="closure-child",
            kid_vorname="Sensitive", kid_nachname="Child",
            anmelder_vorname="Parent", anmelder_nachname="Person",
            rechnungsadresse="Street 1", rechnung_ort="Vienna",
            rechnung_land="Austria",
        )

    def event(self, *, turnus=None, action, details, resource_type="audit_log",
              resource_id="1", resource_label="Audit resource"):
        return AuditEvent.objects._create_validated_event(
            turnus=turnus or self.turnus, actor_id=self.actor.id,
            actor_label="Retained Actor", action=action, outcome="success",
            resource_type=resource_type, resource_id=resource_id,
            resource_label=resource_label,
            request_id=f"closure-{action}-{AuditEvent.objects.count()}",
            client_ip="192.0.2.10", user_agent="Closure Browser",
            details=details,
        )

    def ledger(self, turnus, request_id):
        return HappyCleaningCommandRequest.objects.create(
            turnus=turnus, actor_id=self.actor.id, request_id=request_id,
            action="kid.edit", response={"status": "updated"},
            fingerprint="sha256:" + "a" * 64, status_code=200,
        )

    def test_audit_event_is_absent_from_django_admin(self):
        self.assertNotIn(AuditEvent, admin.site._registry)

    def test_snapshots_outlive_actor_and_child_then_follow_turnus_retention(self):
        ordinary = self.event(
            action="happy_cleaning.event.create",
            details={"happy_cleaning_number": 1},
        )
        kid_details = valid_details()
        kid = self.event(
            action="kid.edit", details=kid_details, resource_type="child",
            resource_id=str(self.child.id),
            resource_label="Sensitive Child snapshot",
        )
        view = self.event(
            action="audit.view",
            details={
                "view_kind": "detail", "result_count": 1,
                "filter_count": 0, "audit_event_id": kid.id,
                "snapshot_id": kid.id, "sensitive_payload_count": 1,
            },
            resource_type="audit_event", resource_id=str(kid.id),
        )
        export = self.event(
            action="audit.export",
            details={"result_count": 2, "filter_count": 0},
            resource_id=str(self.turnus.id),
        )
        ledger = self.ledger(self.turnus, "target-ledger")
        other = self.event(
            turnus=self.other_turnus, action="audit.export",
            details={"result_count": 0, "filter_count": 0},
            resource_id=str(self.other_turnus.id),
        )
        other_ledger = self.ledger(self.other_turnus, "other-ledger")
        target_ids = {ordinary.id, kid.id, view.id, export.id}

        with self.assertRaises(ValidationError):
            ordinary.delete()

        actor_id = self.actor.id
        child_id = self.child.id
        expected_details = deepcopy(kid.details)
        self.child.delete()
        kid.refresh_from_db()
        self.assertEqual(kid.resource_type, "child")
        self.assertEqual(kid.resource_id, str(child_id))
        self.assertEqual(kid.resource_label, "Sensitive Child snapshot")
        self.assertEqual(kid.details, expected_details)

        self.actor.delete()
        kid.refresh_from_db()
        self.assertEqual(kid.actor_id, actor_id)
        self.assertEqual(kid.actor_label, "Retained Actor")
        self.assertEqual(kid.details, expected_details)

        self.turnus.delete()
        self.assertFalse(AuditEvent.objects.filter(id__in=target_ids).exists())
        self.assertFalse(
            HappyCleaningCommandRequest.objects.filter(pk=ledger.pk).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(pk=other.pk).exists())
        self.assertTrue(HappyCleaningCommandRequest.objects.filter(
            pk=other_ledger.pk,
        ).exists())
