# #164-04 repair GREEN — safe authentication and scope-denial logs

Date: 2026-07-31

The P2 repair and its fixture correction are green.

## Focused direct-PostgreSQL verification

A unique direct PostgreSQL database was created and dropped around the bounded
60-second run:

```text
python manage.py test budo_app.audit_tests.test_audit_policy --verbosity 1
```

Result: 8/8 passed in 3.863 seconds. Django system checks passed.

The final fixture preserves the exact required `actor_id` metadata assertion.
It avoids treating an equal numeric actor/Turnus ID as a privacy leak by checking
the complete fixed log record and explicitly excluding Turnus, query, filter,
and synthetic secret content.

Additional verification:

- legacy audit controls: 10/10 passed;
- Python compilation: clean;
- scoped diff review: clean.

No production, staging, commit, or push changes were made by this verification
pass.
