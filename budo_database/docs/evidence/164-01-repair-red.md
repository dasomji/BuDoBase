# #164-01 repair RED — storage matrix and change-path seam

Date: 2026-07-31

This is a tests-only repair pass against the concurrently present #164-01
implementation. This pass did not edit `budo_app/audit.py`,
`budo_app/kid_edit_audit.py`, producers, readers, migrations, or staging state.

## Added contract coverage

`budo_app/audit_tests/test_kid_edit_audit_schema.py` now also specifies:

- structural/canonical `changed_paths` validation does not recompute paths from
  raw before/after differences, because storage-faithful incidental differences
  are allowed;
- `validate_kid_edit_details(..., expected_changed_paths=...)` lets the producer
  plan require exact value and order equality, rejecting missing, extra, and
  reordered paths;
- a literal, non-derived 27-field audit-storage matrix for JSON type, model
  nullability, and exact string limit, with max and max+1 cases for every string;
- non-null but empty-string-capable registrant names, `budo_family` 30/31,
  strict date strings, nullable booleans, PostgreSQL signed integer bounds, and
  boolean/float/NaN exclusion;
- strict non-null ISO period starts whose null/mixed/malformed inputs always raise
  `ValidationError`, never a sorting `TypeError`;
- representative bytes, tuple, lazy value, custom mapping, non-string key, and
  nested SWP/focus/HC/target key rejection.

## Focused direct-PostgreSQL RED run

The final evidence run used the repository `.env` with the pooler hostname
converted to its direct PostgreSQL hostname. A unique temporary database was
created and dropped via `psycopg2`:

```text
python manage.py test budo_app.audit_tests.test_kid_edit_audit_schema --verbosity 0
```

Result: expected RED, exit 1. Sixteen test methods ran in 3.455 seconds. There
were six failing assertions and four errors, isolated to the reviewed defects:

- incidental raw differences are still rejected;
- the explicit `expected_changed_paths` capability is absent;
- mixed null/string period starts leak `TypeError` in ordering;
- null registrant first/last names are accepted despite non-null storage;
- `budo_family` accepts 31 characters despite its 30-character model column;
- `stay_weeks` accepts values outside PostgreSQL's signed 32-bit range;
- a custom `dict` subclass is accepted rather than requiring a plain JSON object.

All remaining methods passed, including the complete valid example, dedicated
4 MiB boundary, envelope dispatch, exact key/path and representative type rules,
and both unchanged generic audit-validator regression controls.
