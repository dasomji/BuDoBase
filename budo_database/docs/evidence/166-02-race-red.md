# #166 PostgreSQL race RED

Date: 2026-07-31

Focused command:

```text
python manage.py test --noinput -v 2 budo_app.kid_edit_tests.test_producer_races
```

Result: 8 tests ran in 27.091 seconds. Two race contracts passed and six
failed. The failures showed that concurrent identical idempotency keys were
validated as stale before ledger replay, different payloads using one key
returned a generic stale conflict instead of `request_id_conflict`, and
aggregate races with standalone number/assignment writers could reach the
bounded PostgreSQL lock timeout. The suite also exposed test-connection
cleanup that must be tightened before the GREEN evidence run.

This is the intended RED result before repairing the command lock order and
idempotency sequencing.
