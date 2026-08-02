# #164-03 repair RED — candidate identity and structural paths

Date: 2026-07-31

Scope: two management-command test regressions and evidence only. Production,
staging, commits, and pushes were untouched.

## Review regressions

`budo_app/audit_tests/test_kid_edit_audit_preflight_command.py` now requires:

- a nonexistent positive, zero, or negative explicit `--turnus-id` raises the
  same fixed non-sensitive `CommandError` (`Candidate Turnus is unavailable.`),
  emits neither the supplied ID nor a misleading `checked=0`, and cannot pass as
  an empty candidate;
- an existing candidate Turnus with zero children remains a successful zero
  aggregate;
- a missing nullable scalar key reports its deterministic known path
  `fields.siblings`;
- an unknown scalar key reports `fields.unexpected_field` deterministically;
- neither structural failure emits the unknown value or synthetic child names.

## Focused direct-PostgreSQL RED

A unique direct PostgreSQL database was created and dropped via `psycopg2` around:

```text
python manage.py test \
  budo_app.audit_tests.test_kid_edit_audit_preflight_command \
  budo_app.audit_tests.test_kid_edit_audit_schema \
  --verbosity 1
```

Result: expected RED, exit 1. Twenty-seven tests ran in 5.478 seconds with five
failing subtests:

- nonexistent, zero, and negative candidate IDs each incorrectly completed as
  an empty successful candidate;
- missing nullable and unknown field structures each fell back to `path=$`
  instead of their deterministic field path.

The real empty-Turnus case passed. All prior preflight cases, all 21 sensitive
schema/generic-validator controls, Python compilation, and Django system checks
remained green.
