"""RED structural contract for the #165 operator runbook repair."""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


RUNBOOK = (
    Path(settings.BASE_DIR) / "docs/operations/audit-security-readiness.md"
)


def section(text, heading, next_heading):
    start = text.index(heading)
    end = text.index(next_heading, start)
    return text[start:end].casefold()


class AuditSecurityReadinessDocumentTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.runbook = RUNBOOK.read_text(encoding="utf-8")

    def assert_section_contract(self, content, requirements):
        for _label, pattern in requirements:
            self.assertRegex(content, pattern)

    def test_permission_inventory_has_an_executable_effective_access_procedure(self):
        content = section(
            self.runbook,
            "### Permission assignments",
            "### Restore and deletion reconciliation",
        )
        self.assert_section_contract(content, (
            ("direct grants", r"direct.{0,80}(grant|assignment)"),
            ("group-derived grants", r"group[- ]derived.{0,80}(grant|assignment)"),
            ("superusers", r"superusers?"),
            ("inactive principals", r"inactive.{0,40}(account|principal|user)"),
            ("non-staff principals", r"non[- ]staff.{0,40}(account|principal|user)"),
            ("view permission", r"view_auditevent"),
            ("export permission", r"export_auditevent"),
            ("effective view count", r"effective.{0,40}view.{0,40}count"),
            ("effective export count", r"effective.{0,40}export.{0,40}count"),
            ("executable procedure", r"python manage\.py (shell|[a-z0-9_-]+)"),
            (
                "permission-bearing group IDs",
                r'"permission_group_id"',
            ),
            (
                "group permission codenames",
                r'"permission_codenames"',
            ),
            (
                "exact group member mapping",
                r'"member_principal_ids"',
            ),
        ))

    def test_restore_drill_reconciles_every_external_register_entry_before_access(self):
        content = section(
            self.runbook,
            "### Restore and deletion reconciliation",
            "### Incident response",
        )
        self.assert_section_contract(content, (
            (
                "external metadata-only register",
                r"external.{0,80}metadata[- ]only.{0,80}deletion register",
            ),
            ("register Turnus key", r"`turnus_id`"),
            ("register deletion timestamp", r"`deleted_at`"),
            ("all applicable entries", r"(all|every).{0,60}(entries|entry)"),
            (
                "delete before access",
                r"delet(e|ed|ion).{0,100}before ordinary access",
            ),
            ("zero residual rows", r"zero.{0,60}residual"),
            (
                "unrelated control survives",
                r"(control|unrelated) turnus.{0,80}(remain|surviv)",
            ),
        ))
        self.assertNotRegex(
            content,
            r"if\s+deleted_at\s*(>|>=|<|<=)\s*backup_at",
            "deletion timestamp must never filter safety target IDs",
        )
        self.assert_section_contract(content, (
            (
                "every valid entry contributes a safety target",
                r"every valid register entry[\s\S]{0,100}target_ids",
            ),
            (
                "timestamp is diagnostic only",
                r"deleted_at[\s\S]{0,100}diagnostic only",
            ),
            (
                "all listed restored Turnuses are absent",
                r"all listed restored turnus(es)?[\s\S]{0,100}absent",
            ),
        ))
