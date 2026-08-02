# #164-04 repair RED — safe authentication and scope-denial logs

Date: 2026-07-31

Scope: two compact authorization logging regressions and evidence only. No access
event is required for denied requests. Production, staging, commits, and pushes
were untouched.

## Review regressions

`budo_app/audit_tests/test_audit_policy.py` now requires:

- authorized ordinary users selecting a foreign, nonexistent, or malformed
  explicit Turnus receive 404 only after a fixed
  `scope_unavailable` warning is emitted;
- the same three unavailable scopes on export emit the fixed export warning
  before 404;
- those warnings contain only authenticated actor ID, endpoint kind, and fixed
  reason code—never the submitted Turnus ID, query string, or filter values;
- anonymous list and export requests retain DRF's authentication denial status
  while emitting fixed `authentication_required` metadata with
  `actor_id=None` and endpoint kind;
- anonymous warnings likewise omit all submitted scope and filter values.

Expected fixed format:

```text
audit_access_denied actor_id=<id-or-None> endpoint=<list-or-export> reason=<code>
```

## Clean focused direct-PostgreSQL RED

A unique direct PostgreSQL database was created and dropped around a 60-second
bounded run:

```text
python manage.py test budo_app.audit_tests.test_audit_policy --verbosity 1
```

Result: expected RED, exit 1. Eight methods ran in 3.208 seconds with eight
failing subtests and no errors or hangs:

- two anonymous endpoint cases emitted no `authentication_required` warning;
- six unavailable-scope combinations (three scopes across list and export)
  emitted no `scope_unavailable` warning.

All original #164-04 policy, effective-bootstrap, denial-ordering, and Turnus
scope methods passed at this fixed point. Python compilation and Django system
checks were clean.
