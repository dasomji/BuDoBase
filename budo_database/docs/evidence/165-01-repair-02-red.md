# #165-01 repair-02 RED — final evidence and reconciliation gaps

Date: 2026-07-31

Scope: tests and RED evidence only. No validator, canonical manifest,
operations runbook, production assertion, staging, commit, or push was changed
by this pass.

## Three-finding contract

1. Evidence references reject every expanded placeholder token (TODO, TBD,
   unknown, none, unassigned, sample, example, fake, and dummy) with only the
   JSON pointer and fixed reason; the injected reference is never echoed.
2. The permission inventory emits each permission-bearing group ID, its audit
   permission codenames, and the exact member principal IDs so the group grant
   can be reconciled as an explicit group-to-principal mapping.
3. Every valid external deletion-register entry contributes its `turnus_id` to
   safety `target_ids`. `deleted_at` and the backup timestamp are diagnostic
   context only, never a filter. The script deletes and asserts every listed
   restored Turnus absent before ordinary access.

## Clean local RED

```text
python manage.py test --noinput --verbosity 1 \
  budo_app.audit_tests.test_audit_security_readiness_command \
  budo_app.audit_tests.test_audit_security_readiness_document
```

Result: expected RED, exit 1. Ten tests ran in 0.062 seconds with exactly three
focused failures, no errors, no hangs, and a clean Django system check. The
failures correspond one-to-one with the three findings: an expanded placeholder
inside an HTTPS evidence reference is accepted; permission-bearing group/member
mapping is absent; and `if deleted_at > backup_at` still filters deletion safety
targets. The seven unaffected readiness tests remain green.

Python compilation and scoped diff whitespace checks were clean.
