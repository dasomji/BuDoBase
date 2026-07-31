# #164-01 repair-02 RED — token, bigint, and blank storage values

Date: 2026-07-31

Scope: tests and evidence only. This pass did not edit production, producers,
readers, migrations, staging state, or commits.

## Contract additions

`budo_app/audit_tests/test_kid_edit_audit_schema.py` now specifies:

- exact `v1.<43 url-safe characters>` and
  `legacy:v1.<43 url-safe characters>` token syntax is rejected in every one of
  the 23 arbitrary-string scalar fields;
- both token syntaxes are rejected in representative period, focus, event, and
  station labels;
- short token-like but non-token raw strings remain accepted and are reconstructed
  byte-for-byte across all those scalar and relationship locations;
- the outer decimal child resource ID accepts `9223372036854775807` and rejects
  `9223372036854775808`;
- storage-faithful empty strings for `period_code`, focus label, and station label
  are accepted and reconstructed exactly. Derived period/event labels remain
  nonblank under the existing contract.

## Focused direct-PostgreSQL RED run

A unique direct-PostgreSQL database was created and dropped via `psycopg2` around:

```text
python manage.py test budo_app.audit_tests.test_kid_edit_audit_schema --verbosity 0
```

Result: expected RED, exit 1. Twenty-one test methods ran in 4.504 seconds with
53 failing subtest assertions and 3 errors:

- 44 scalar token cases were accepted (the two `budo_family` cases are already
  rejected by that column's shorter 30-character limit);
- all 8 relationship-label token cases were accepted;
- the one-above-signed-bigint child resource ID was accepted;
- blank period code, focus label, and station label were each rejected.

The exact signed-bigint maximum, all token-like non-token raw controls, and every
pre-existing contract method passed. This includes the dedicated 4 MiB boundary,
the repaired storage/path/type suite, envelope behavior, and both unchanged
generic audit-validator regression controls.
