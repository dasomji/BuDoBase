# #164-06 repair RED — detail path bounds and later list summary

Date: 2026-07-31

Scope: two compact detail/list review findings and evidence only. No
production, staging, commit, or push change was made.

## Review regressions

- ID bounds are explicit: zero, negative, and nonnumeric paths do not resolve;
  a syntactically positive ID above signed PostgreSQL bigint maximum reaches
  the protected detail policy but returns the same safe 404 and fixed
  `scope_unavailable` log as a missing ID. Neither path performs audit lookup,
  serialization, or access insertion.
- When a detail `audit.view` row appears in a later list snapshot, its summary
  is value-free and kind-specific:

```json
{
  "sensitive": false,
  "available_fields": [
    "audit_event_id",
    "filter_count",
    "result_count",
    "sensitive_payload_count",
    "snapshot_id",
    "view_kind"
  ]
}
```

Projecting only `view_kind` lets the list select this schema without loading
the complete details JSON. A union of list/detail field names would also be
safe, but the kind-specific contract is more accurate and remains bounded.

## Clean focused direct-PostgreSQL RED

A unique direct PostgreSQL database was created around one 60-second bounded
run:

```text
python manage.py test --noinput -v 1 \
  budo_app.audit_tests.test_audit_detail_contract
```

Result: expected RED, exit 1. Eleven methods ran in 4.267 seconds with one
focused failure, no errors, no hangs, and a clean Django system check. Every
detail endpoint, invalid-path, oversized-ID, logging, no-lookup, access-event,
scope, and privacy control passed. The sole failure showed that a later detail
access row still advertises list-only `page`/`page_size` fields instead of the
detail-only `audit_event_id` field.

Django destroyed its test database and the uniquely prefixed base database was
dropped successfully. Python compilation and scoped diff whitespace checks
were clean.
