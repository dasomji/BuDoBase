# Audit security readiness gate

This runbook is the human/operator gate required by
[#158](https://github.com/dasomji/BuDoBase/issues/158) and tracked by
[#165](https://github.com/dasomji/BuDoBase/issues/165) in
[`dasomji/BuDoBase`](https://github.com/dasomji/BuDoBase). It must be completed
before audit data is exposed in production. Repository tests and development
QA do not establish production security controls.

The machine-readable record is
`docs/operations/audit-security-readiness.json`. The committed record is
deliberately blocked until production owners verify every control and a named
approver records a dated evidence reference.

## Gate commands

Lint the canonical manifest without claiming approval:

```text
python manage.py check_audit_security_readiness
```

Require a complete approval before a production release:

```text
python manage.py check_audit_security_readiness --require-approved
```

An operator may lint a candidate file with `--manifest /path/to/file.json`.
The command prints only the overall status. Validation errors contain a JSON
pointer and a fixed reason; they do not echo manifest values.

## Candidate-data preflight

1. Confirm the production candidate has migration `0083_kid_edit_foundation`
   applied using the deployment's read-only migration inspection procedure.
2. Run `check_kid_edit_audit_payloads` against the candidate Turnus, or without
   `--turnus-id` when the approved procedure calls for all children.
3. Capture only the aggregate `checked`, `supported`, `unsupported`,
   `total_bytes`, `max_bytes`, and `limit_bytes` output. Unsupported diagnostic
   lines may contain only child ordinal, structural path, and encoded size.
4. Record the date and repository evidence path. A passing preflight requires
   `supported + unsupported = checked`, zero unsupported children, and a
   maximum no larger than the limit.

The committed development/QA aggregate is recorded only in `qa_preflight` and
is useful rehearsal evidence only. It must never be copied into
`candidate_preflight`. Keep the candidate status blocked and every other
candidate field null until an authorized operator runs the preflight in the
production environment against an approved production clone. An eligible run
uses provenance `approved-production-clone`, records its operator-controlled
date and evidence reference, and must have complete passing counts and sizes.

## Required production controls

For each control, the responsible role records `verified`, a real verification
date, and a safe repository path or HTTPS evidence URL. Evidence must contain
no credentials, tokens, personal data, or secret-bearing URL components.

### Storage encryption

Verify encryption at rest for the primary database, replicas, snapshots, and
backup media that can contain audit rows. Record the production configuration
or provider attestation used for the decision.

### Database transport

Verify encrypted database connections, certificate validation, and the
application's production connection policy. Exercise a failing configuration
to show that insecure transport is not silently accepted.

### Browser transport

Verify HTTPS enforcement, redirect behavior, HSTS policy, secure session
cookies, and the absence of mixed-content access to audit list, detail, and
export endpoints.

### Credentials and MFA

Verify that production database, deployment, backup, and administrative
credentials are held in the approved secret system; access is least-privilege;
MFA is enforced for human control-plane access; and rotation/revocation
procedures are current.

### Logging exclusions

Inspect application, proxy, platform, database, tracing, and error-reporting
outputs. Confirm that audit payloads, export bodies, cookies, credentials,
health data, and URL secrets are excluded. Retain only the fixed metadata
needed for authorization-denial diagnostics.

### Backup and export handling

Verify encryption, access control, retention, deletion, and transfer rules for
backups and downloaded full-payload exports. Confirm that export handling is
documented for operators and that temporary or shared copies are controlled.

### Permission assignments

Run the following read-only inventory in the production application release.
It inventories direct grant assignments, group-derived grant assignments,
superusers, inactive accounts, and non-staff accounts. It also reports the
effective view count and effective export count after applying the same active,
staff, and permission intersection as the application. Output contains IDs and
counts, not names or audit data.

```bash
python manage.py shell <<'PY'
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()
users = list(User.objects.prefetch_related(
    "user_permissions", "groups__permissions",
).order_by("pk"))
view = "budo_app.view_auditevent"
export = "budo_app.export_auditevent"

def direct(user, codename):
    return user.user_permissions.filter(
        content_type__app_label="budo_app", codename=codename,
    ).exists()

def group_derived(user, codename):
    return user.groups.filter(
        permissions__content_type__app_label="budo_app",
        permissions__codename=codename,
    ).exists()

def eligible(user):
    return user.is_active and user.is_staff

permission_groups = Group.objects.filter(
    permissions__content_type__app_label="budo_app",
    permissions__codename__in=("view_auditevent", "export_auditevent"),
).distinct().order_by("pk")
for group in permission_groups:
    permission_codenames = sorted(group.permissions.filter(
        content_type__app_label="budo_app",
        codename__in=("view_auditevent", "export_auditevent"),
    ).values_list("codename", flat=True))
    member_principal_ids = sorted(group.user_set.values_list("pk", flat=True))
    print(json.dumps({
        "permission_group_id": group.pk,
        "permission_codenames": permission_codenames,
        "member_principal_ids": member_principal_ids,
    }, sort_keys=True))

for user in users:
    assigned = any((
        direct(user, "view_auditevent"), direct(user, "export_auditevent"),
        group_derived(user, "view_auditevent"),
        group_derived(user, "export_auditevent"), user.is_superuser,
    ))
    if assigned:
        print(
            "principal_id", user.pk,
            "direct_view", direct(user, "view_auditevent"),
            "direct_export", direct(user, "export_auditevent"),
            "group_view", group_derived(user, "view_auditevent"),
            "group_export", group_derived(user, "export_auditevent"),
            "superuser", user.is_superuser,
            "inactive_account", not user.is_active,
            "non_staff_account", not user.is_staff,
        )

effective_view = [u.pk for u in users if eligible(u) and u.has_perm(view)]
effective_export = [
    u.pk for u in users
    if eligible(u) and u.has_perm(view) and u.has_perm(export)
]
print("effective_view_count", len(effective_view))
print("effective_export_count", len(effective_export))
PY
```

Reconcile every reported principal with the approved access roster. Explain or
remove direct and group-derived assignments that are not on the roster; treat
superusers as effective grants; and remove audit access from inactive or
non-staff principals even when a raw assignment exists. Record the two
effective counts, the reconciliation result, reviewer role, date, and a safe
evidence reference. Confirm least privilege, Turnus scope,
joiner/mover/leaver handling, and periodic recertification.

### Restore and deletion reconciliation

Maintain an external metadata-only deletion register outside the application
database and its backups. Each JSON Lines entry has exactly two fields:
`turnus_id` (a positive integer) and `deleted_at` (the UTC deletion timestamp).
It contains no child, actor, audit-payload, or free-text values. Append an entry
for every committed Turnus deletion, and protect the register with the same
restricted operational access and integrity controls as restore evidence.

For an approved restore drill, record the backup timestamp and an unrelated
control Turnus ID. Restore into an isolated environment with ordinary access
disabled. Every valid register entry contributes its `turnus_id` to
`target_ids`; `deleted_at` and the backup timestamp are diagnostic only and
never filter the safety target. Delete before ordinary access every restored
Turnus selected by the register. The reconciliation is executable after supplying
the approved external register and timestamps:

Export `AUDIT_DELETION_REGISTER`, `AUDIT_RESTORE_BACKUP_AT`, and
`AUDIT_RESTORE_CONTROL_TURNUS_ID` to the approved exercise's actual register,
UTC backup timestamp, and existing unrelated control ID. Then run:

```bash
python manage.py shell <<'PY'
import json
import os
from datetime import datetime
from django.apps import apps
from django.db import transaction
from budo_app.models import AuditEvent, HappyCleaningCommandRequest, Turnus

backup_at = datetime.fromisoformat(os.environ["AUDIT_RESTORE_BACKUP_AT"])
control_id = int(os.environ["AUDIT_RESTORE_CONTROL_TURNUS_ID"])
entries = []
with open(os.environ["AUDIT_DELETION_REGISTER"], encoding="utf-8") as register:
    for line in register:
        entry = json.loads(line)
        assert set(entry) == {"turnus_id", "deleted_at"}
        assert type(entry["turnus_id"]) is int and entry["turnus_id"] > 0
        deleted_at = datetime.fromisoformat(entry["deleted_at"])
        assert deleted_at.tzinfo is not None
        entries.append((entry["turnus_id"], deleted_at))

target_ids = sorted({turnus_id for turnus_id, _ in entries})
deletions_after_backup = sum(
    deleted_at > backup_at for _, deleted_at in entries
)
assert control_id not in target_ids
with transaction.atomic():
    for turnus_id in target_ids:
        Turnus.objects.filter(pk=turnus_id).delete()

assert not AuditEvent.objects.filter(turnus_id__in=target_ids).exists()
assert not HappyCleaningCommandRequest.objects.filter(
    turnus_id__in=target_ids,
).exists()
assert not Turnus.objects.filter(pk__in=target_ids).exists()
for model in apps.get_models():
    if any(field.name == "turnus" for field in model._meta.fields):
        assert not model._default_manager.filter(
            turnus_id__in=target_ids,
        ).exists(), model._meta.label
assert Turnus.objects.filter(pk=control_id).exists()
print("applicable_deletion_entries", len(entries))
print("deletions_after_backup_diagnostic", deletions_after_backup)
print("deleted_turnus_count", len(target_ids))
print("zero_residual_audit_ledger_domain_rows", True)
print("control_turnus_survives", True)
PY
```

Reconcile all entries, including duplicate entries for an already deleted
Turnus. Prove all listed restored Turnuses are absent. Require zero residual
audit, command-ledger, and domain rows for the deleted IDs, while the unrelated
control Turnus and its rows survive.
Record counts and query evidence only. Any malformed or missing register entry,
failed deletion, non-zero residual, missing control Turnus, or other assertion
failure blocks the restore and ordinary access until investigated and rerun.

### Incident response

Verify the response procedure for unauthorized audit viewing or export. It must
cover containment, credential revocation, evidence preservation without
payload spreading, scope assessment, required notification decisions,
recovery, and post-incident permission review.

## At-rest decision

The at-rest decision is separate from individual control checks. Use `pending`
with null decision fields while the first decision awaits evidence. Use
`reopen-required`, also with null decision fields, when a material change makes
the prior basis stale and a new decision has not yet been recorded. Both states
block approval.

After a passing eligible candidate run and complete production evidence, a
named data owner may record `accepted` with the actual decision date and an
existing safe evidence reference. Approval requires this accepted state. If a
candidate preflight fails or a previously accepted basis is invalidated, record
`reopened` with the responsible owner, date, and evidence reference; resolve the
failure and obtain a new acceptance before approval.

## Approval procedure

1. Keep the top-level status and approval status `blocked` while any control is
   blocked. The blocker list must exactly match blocked controls.
2. A responsible operator verifies every control from production evidence and
   records the role, date, and evidence reference in the manifest.
3. A named production security approver reviews the complete record. Only that
   human may set both statuses to `approved`, clear blockers, and add the dated
   approval evidence reference.
4. Run the lint command, then the `--require-approved` gate in the release
   workflow. Preserve its result with the release evidence.
5. Reopen the gate after material infrastructure, credential, retention,
   permission, backup, incident-process, or audit-payload changes.

The repository does not infer approval from passing tests, development data,
provider defaults, or an absent answer.

## Runtime release gate

Production exposes the kid-edit producer and read contract, its Edit entry
point, and the audit page, detail, export, and navigation surfaces only when
this manifest validates with status `approved`. The gate fails closed when the
manifest is missing, unreadable, invalid, or blocked.

For development or QA only, set `BUDO_KID_EDIT_ALLOW_UNAPPROVED=1` to bypass
the manifest decision. Do not use this override for production releases.
