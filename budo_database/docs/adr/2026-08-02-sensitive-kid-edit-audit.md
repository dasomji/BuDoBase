# Store complete kid-edit snapshots behind the hardened audit boundary

- **Status:** Accepted
- **Date:** 2026-08-02
- **Schema validation:** `budo_app/kid_edit_audit.py`
- **Snapshot construction:** `budo_app/kid_edit_audit_snapshot.py`
- **Authorization policy:** `budo_app/audit_policy.py`
- **Operations runbook:** [`docs/operations/audit-security-readiness.md`](../operations/audit-security-readiness.md)
- **Original design:** [GitHub issue #158](https://github.com/dasomji/BuDoBase/issues/158)

## Context

A successful complete child edit must be reconstructable later. The edited
projection includes health, family, contact, Schwerpunkt, and Happy Cleaning
data, so its history is substantially more sensitive than ordinary operational
audit metadata.

The generic audit validator intentionally rejects sensitive-looking keys and
large details. Weakening that validator would broaden every existing audit
action. Returning complete details in audit lists, admin pages, or bootstrap
responses would also expose many records without an explicit reveal.

The application already stores current child data in PostgreSQL. A separate
encrypted history store or an application-managed encryption-key lifecycle was
not selected for this feature.

## Decision

Every successful canonical child-edit mutation writes exactly one immutable,
schema-versioned `kid.edit` event in `AuditEvent`. It contains complete,
storage-faithful before and after snapshots and an ordered set of changed paths.
The event is inserted inside the aggregate transaction; audit validation or
insertion failure aborts the complete edit.

No event is created for a canonical no-op, replay, validation error, conflict,
or failed transaction. Submitted sensitive values are not copied into errors,
logs, command-ledger responses, URLs, analytics, or rejection audit records.

### Dedicated schema boundary

`kid.edit` uses its own exact validator and a maximum compact UTF-8 payload size
of 4 MiB. The existing generic audit validator and its smaller redacted boundary
remain unchanged for all other actions. The dedicated validator rejects unknown
keys, invalid types and shapes, baseline/preserve tokens, and snapshots that do
not match the independently projected summary.

Snapshots preserve storage meaning, including null versus empty values and
valid legacy representations. They contain the full configured child-edit
projection so a later rename or relationship change does not erase historical
meaning.

### Access policy

The accepted policy is the one centralized in `budo_app/audit_policy.py`:

- viewing requires an authenticated, active Django staff user with
  `budo_app.view_auditevent`;
- exporting additionally requires `budo_app.export_auditevent`;
- nonstaff users remain denied even if a raw permission is assigned;
- superusers use normal Django permission resolution and must still be active
  staff.

In project terminology, these eligible staff accounts are the administrators
allowed to read audit history. The server policy is authoritative; hiding a
navigation item is not authorization.

All browser, list, detail, export, and bootstrap surfaces consume the centralized
policy. Denial occurs before audit filtering or serialization.

### Read and export boundary

Audit lists return bounded summaries under stable snapshot pagination. They do
not include complete `kid.edit` details. One explicit detail request may reveal
one scoped event and records a metadata-only `audit.view` event before releasing
the payload. If access auditing fails, the sensitive payload is not returned.

Exports require the additional export permission, record issuance metadata, and
stream the authorized scope rather than staging a server-side file. Audit
responses use private/no-store cache controls. `AuditEvent` is not exposed
through Django admin.

### Trust and operational boundary

The JSON payload is stored in the existing PostgreSQL audit row without
application-level field encryption. Database, backup, and hosting operators are
therefore inside the trust boundary. Turnus deletion cascades to its audit and
command-ledger history; restored backups require reconciliation with the
external Turnus deletion register.

The operations runbook and its machine-readable manifest remain the factual
source for deployment-control evidence. Product acceptance of this architecture
must not be represented as evidence that storage, transport, MFA, logging,
backup, or restore controls were technically verified when they were not.

## Consequences

- Authorized administrators can reconstruct a complete successful child edit.
- A database or backup operator with sufficient access can read these snapshots;
  application authorization does not encrypt data at rest.
- New audit readers must default to summaries and use explicit, scoped reveal
  for complete details.
- Changes to the snapshot schema require a new schema version and compatibility
  handling rather than silently changing version 1.
- Tests and operational evidence must use synthetic values and must not retain
  real child payloads.

## Rejected alternatives

- **Changed fields only:** cannot reconstruct the complete state independently.
- **Relax the generic audit validator:** expands the sensitive surface of every
  audit action.
- **Put full details in list rows or Django admin:** fetches and exposes many
  sensitive records without explicit intent.
- **Truncate oversized snapshots:** destroys reconstructability and hides an
  unsupported state.
- **Add feature-local application encryption:** introduces key custody, rotation,
  restore, and permanent key-loss risks without protecting current child rows.
- **Keep an indefinite external archive:** conflicts with Turnus-scoped
  retention.

## Verification references

The durable executable specification lives in:

- `budo_app/audit_tests/test_kid_edit_audit_schema.py`
- `budo_app/audit_tests/test_kid_edit_audit_snapshot.py`
- `budo_app/audit_tests/test_audit_policy.py`
- `budo_app/audit_tests/test_audit_list_contract.py`
- `budo_app/audit_tests/test_audit_detail_contract.py`
- `budo_app/audit_tests/test_audit_export_v2_contract.py`
- `budo_app/audit_tests/test_audit_security_readiness_document.py`
