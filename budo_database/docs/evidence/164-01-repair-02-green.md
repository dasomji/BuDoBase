# #164-01 repair-02 GREEN — token non-retention and storage blanks

Date: 2026-07-31

Further hardened the dedicated `budo.kid-edit` audit boundary without adding a
producer or reader and without changing generic audit behavior.

## Repaired behavior

- Exact ordinary baseline syntax (`v1.` plus a 43-character URL-safe digest)
  and exact legacy-preserve syntax (`legacy:v1.` plus that digest) are rejected
  from every audited string scalar and relationship label.
- Token-like raw storage values that do not match the complete syntax, such as
  `v1.A` and `legacy:v1.B`, are preserved and reconstructed exactly.
- The validator reuses the centralized signing syntax checks; it does not
  attempt signature verification or retain token values.
- Storage-faithful blank period codes, focus labels, and station labels are
  accepted and reconstructed exactly. Derived period and event display labels
  retain their nonblank and length requirements.
- The outer `kid.edit` child resource ID accepts canonical positive decimal
  values through signed PostgreSQL bigint maximum and rejects the next value.
- The 4 MiB detail limit, explicit 27-field storage schema, producer-plan path
  validation, strict built-in JSON containers, and generic audit isolation are
  unchanged.

## Focused direct-PostgreSQL verification

Fresh direct PostgreSQL database, without `--keepdb`:

```text
python manage.py test --noinput -v 1 \
  budo_app.audit_tests.test_kid_edit_audit_schema

Ran 21 tests in 4.470s — OK
```

Existing audit controls on a second fresh database:

```text
python manage.py test --noinput -v 1 budo_app.audit_tests.test_audit

Ran 10 tests in 6.834s — OK
```

Both databases were destroyed successfully and Django's system check reported
no issues.

## Controls

- Python compilation passed for `kid_edit_audit.py` and `audit.py`.
- `git diff --check` passed.
- the staged diff is empty.
- no files were staged and no commit was created.
