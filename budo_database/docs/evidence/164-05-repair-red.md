# #164-05 repair RED — list boundary hardening

Date: 2026-07-31

Scope: representative backend/frontend regressions and evidence only. No
production, one-event detail, export, staging, commit, or push change was made.

## Contract repairs

- Previous/next links preserve `snapshot_id`; filter submission and reset omit it.
- Anonymous/authenticated 403 and unavailable-scope 404 list responses carry the
  exact audit privacy headers.
- `audit.view` list metadata has exact types and natural upper bounds: result
  count <= page size <= 100, filter count <= eight supported filters, and page
  and snapshot <= signed-bigint maximum; oversized generic metadata is rejected.
- Authorization spies target the summary serializer.
- A superuser's explicitly selected Turnus survives in each `details_url`.
- Stored `kid.edit` schema/version fragments are projected and malformed rows
  fail closed rather than being relabeled with hard-coded values.
- The list projection runs on default SQLite as well as PostgreSQL.
- An access-writer `RuntimeError` is sanitized to a payload-free 503 with privacy
  headers, while an unrelated builder `RuntimeError` remains visible.
- Distinct filter options are capped by the reused snapshot.
- Legacy summaries are exactly schema-derived and value-free:
  `{sensitive: false, available_fields: sorted(allowed fields)}`. This portable
  design exposes capabilities, not actual-key presence, and avoids loading full
  details JSON. Summaries remain bounded to 1024 encoded bytes.

## Backend SQLite RED

```text
DATABASE_URL='sqlite:///:memory:' python manage.py test --noinput -v 1 \
  budo_app.audit_tests.test_audit_list_contract \
  budo_app.audit_tests.test_audit_policy
```

Result: expected RED, exit 1. Nineteen methods ran in 0.438 seconds with ten
focused failure reports, no errors, no hangs, and a clean Django system check.
Failures identify missing denial headers, RuntimeError fail-close handling,
exact legacy summaries, explicit-Turnus detail URLs, snapshot-capped options,
stored schema/version validation, and audit-view upper bounds. The SQLite
projection portability regression and unchanged policy controls passed.

## Frontend RED

The worktree temporarily reused the canonical workspace's existing ignored
`node_modules` installation; the link was removed immediately after the run.

```text
npm --prefix frontend test -- --run src/domains/audit.test.jsx
```

Result: expected RED, exit 1. Five tests ran: four controls passed and the new
pagination contract failed because previous/next links omit `snapshot_id`.

Python compilation and scoped diff whitespace checks were clean.
