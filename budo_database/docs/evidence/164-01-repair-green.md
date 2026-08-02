# #164-01 repair GREEN — producer-plan paths and literal storage schema

Date: 2026-07-31

Repaired the dedicated `budo.kid-edit` v1 audit validator without adding a
producer, reader, migration, or UI and without changing the generic audit
validation path.

## Repaired behavior

- Stored `changed_paths` are always required to be nonempty, unique, valid for
  the snapshot configuration, and in canonical field/period/number/event
  order. They are no longer inferred from incidental differences between raw
  storage snapshots.
- `validate_kid_edit_details(..., expected_changed_paths=...)` optionally
  requires exact sequence equality with the producer's planned changed paths.
- A literal, ordered 27-field audit-storage table owns value kinds,
  nullability, and string limits independently of the canonical edit-request
  contract. This includes non-null registrant names, the 30-character
  `budo_family` bound, and PostgreSQL integer bounds.
- Period start dates are non-null and strictly valid ISO dates. Nullable child
  birthdays retain their exact date boundary.
- Only exact built-in `dict` and `list` JSON containers cross the schema
  boundary; subclasses, custom mappings, tuples, floats, NaN, bytes, lazy
  values, mixed invalid dates, and opaque values all fail as `ValidationError`.
- The compact UTF-8 4 MiB inclusive limit, fresh plain-JSON reconstruction,
  exact outer `kid.edit` envelope, and generic audit isolation are preserved.

## Focused direct-PostgreSQL verification

Fresh direct PostgreSQL database, without `--keepdb`:

```text
python manage.py test --noinput -v 1 \
  budo_app.audit_tests.test_kid_edit_audit_schema

Ran 16 tests in 3.233s — OK
```

Existing audit controls on a second fresh database:

```text
python manage.py test --noinput -v 1 budo_app.audit_tests.test_audit

Ran 10 tests in 6.935s — OK
```

Both databases were destroyed successfully and Django's system check reported
no issues.

## Controls

- Python compilation passed for `kid_edit_audit.py` and `audit.py`.
- `git diff --check` passed.
- the staged diff is empty.
- no files were staged and no commit was created.
