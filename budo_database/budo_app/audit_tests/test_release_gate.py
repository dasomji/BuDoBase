"""Runtime release-gate contracts for audit and kid-edit surfaces."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from budo_app.audit_readiness import readiness_approved
from budo_app.models import Kinder, Turnus


def approved_manifest():
    path = Path(settings.BASE_DIR) / "docs/operations/audit-security-readiness.json"
    manifest = deepcopy(json.loads(path.read_text(encoding="utf-8")))
    today = date.today().isoformat()
    manifest["status"] = "approved"
    manifest["reviewed_on"] = today
    manifest["candidate_preflight"] = {
        "status": "passed",
        "environment": "production",
        "provenance": "approved-production-clone",
        "checked_on": today,
        "checked": 1,
        "supported": 1,
        "unsupported": 0,
        "total_bytes": 1,
        "max_bytes": 1,
        "limit_bytes": 4194304,
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    for control in manifest["controls"].values():
        control["status"] = "verified"
        control["verified_on"] = today
    manifest["blockers"] = []
    manifest["at_rest_decision"] = {
        "disposition": "accepted",
        "owner": "Production Data Owner",
        "decided_on": today,
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    manifest["approval"] = {
        "status": "approved",
        "approver": "Production Security Owner",
        "approved_on": today,
        "evidence_ref": "docs/operations/audit-security-readiness.md",
    }
    return manifest


class ReadinessApprovedTests(SimpleTestCase):
    def test_missing_invalid_and_blocked_manifests_are_not_approved(self):
        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            invalid = Path(directory) / "invalid.json"
            invalid.write_text("{invalid", encoding="utf-8")

            self.assertFalse(readiness_approved(missing))
            self.assertFalse(readiness_approved(invalid))
        self.assertFalse(readiness_approved())

    def test_valid_approved_manifest_is_approved(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "approved.json"
            path.write_text(json.dumps(approved_manifest()), encoding="utf-8")

            self.assertTrue(readiness_approved(path))


class ReleaseGateViewTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=165,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(
            username="release-gate", is_staff=True,
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_auditevent"),
            Permission.objects.get(codename="export_auditevent"),
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.kid = Kinder.objects.create(
            kid_index="RELEASE-GATE-KID",
            kid_vorname="Ada",
            kid_nachname="Gate",
            turnus=self.turnus,
        )
        self.client.force_login(self.user)

    def kid_edit_route_data(self):
        return self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "kid-edit"}),
            {"id": self.kid.id},
        )

    @override_settings(KID_EDIT_ALLOW_UNAPPROVED=False)
    def test_blocked_manifest_closes_all_release_surfaces(self):
        gated = {"ok": False, "code": "release_gated"}

        kid_edit = self.client.post(
            reverse("kid-edit-api", kwargs={"kid_id": self.kid.id}),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual((kid_edit.status_code, kid_edit.json()), (403, gated))
        self.assertEqual(
            self.client.get(reverse("audit-page")).status_code, 404,
        )

        detail = self.client.get(
            reverse("audit-event-detail-api", kwargs={"event_id": 1}),
        )
        self.assertEqual((detail.status_code, detail.json()), (403, gated))
        export = self.client.get(reverse("audit-export-api"))
        self.assertEqual((export.status_code, export.json()), (403, gated))

        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertFalse(bootstrap["permissions"]["view_auditevent"])
        self.assertFalse(bootstrap["permissions"]["kid_edit_enabled"])
        route_data = self.kid_edit_route_data()
        self.assertEqual((route_data.status_code, route_data.json()), (403, gated))
        audit_contract = self.client.get(
            reverse("route-data-api", kwargs={"contract_key": "audit"}),
        )
        self.assertEqual(
            (audit_contract.status_code, audit_contract.json()), (403, gated),
        )

    @override_settings(KID_EDIT_ALLOW_UNAPPROVED=True)
    def test_explicit_flag_keeps_development_surface_open(self):
        self.assertEqual(self.kid_edit_route_data().status_code, 200)
        bootstrap = self.client.get(reverse("bootstrap-api")).json()
        self.assertTrue(bootstrap["permissions"]["kid_edit_enabled"])

    @override_settings(KID_EDIT_ALLOW_UNAPPROVED=False)
    @mock.patch("budo_app.audit_readiness.readiness_approved", return_value=True)
    def test_approved_manifest_opens_the_views(self, _approved):
        self.assertEqual(self.client.get(reverse("audit-page")).status_code, 200)
        self.assertEqual(self.kid_edit_route_data().status_code, 200)
        permissions = self.client.get(reverse("bootstrap-api")).json()[
            "permissions"
        ]
        self.assertTrue(permissions["view_auditevent"])
        self.assertTrue(permissions["kid_edit_enabled"])

        kid_edit = self.client.post(
            reverse("kid-edit-api", kwargs={"kid_id": self.kid.id}),
            data="{}",
            content_type="application/json",
        )
        self.assertNotEqual(kid_edit.json().get("code"), "release_gated")
        detail = self.client.get(
            reverse("audit-event-detail-api", kwargs={"event_id": 1}),
        )
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(
            self.client.get(reverse("audit-export-api")).status_code, 200,
        )
