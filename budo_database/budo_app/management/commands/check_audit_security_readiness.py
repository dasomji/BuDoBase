"""Lint the repository audit-security readiness manifest."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from budo_app.audit_readiness import (
    ReadinessError,
    default_manifest_path,
    validate_manifest,
)


class Command(BaseCommand):
    help = "Lint the audit-security readiness manifest without echoing values."

    def add_arguments(self, parser):
        parser.add_argument("--manifest")
        parser.add_argument("--require-approved", action="store_true")

    def handle(self, *args, **options):
        manifest_path = options.get("manifest")
        path = Path(manifest_path) if manifest_path else default_manifest_path()
        try:
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise ReadinessError("/: manifest could not be read as JSON")
            validate_manifest(manifest)
            if (
                options.get("require_approved")
                and manifest["status"] != "approved"
            ):
                raise ReadinessError("/status: approved readiness is required")
        except ReadinessError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(f"audit_security_readiness status={manifest['status']}")
