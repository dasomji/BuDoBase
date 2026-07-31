# #165-01 repair RED — provenance and operational closure

Date: 2026-07-31

Scope: repair tests and evidence only. No validator, canonical manifest,
operations runbook, production assertion, staging, commit, or push was changed
by this pass.

## Repair contract

- Development/QA aggregates remain separate rehearsal evidence. A blocked
  candidate has no eligible-run provenance, environment, counts, date, size, or
  evidence values; approval requires an exact `approved-production-clone`
  provenance from the production environment.
- The exact manifest includes an at-rest decision. Pending or reopen-required
  dispositions keep readiness blocked; approval requires a named, dated,
  evidenced acceptance; a failed/reopened gate requires a named, dated,
  evidenced `reopened` decision.
- Placeholder rejection also covers TODO, TBD, unknown, none, unassigned,
  sample, example, fake, and dummy assertions.
- Repository evidence paths must be normalized existing regular files below
  `docs/`. Safe HTTPS references remain syntactically acceptable and do not
  become machine-verified statements of truth.
- The operations runbook must define an executable permission inventory across
  direct grants, group-derived grants, superusers, inactive/non-staff
  principals, and effective counts for both audit permissions.
- The restore procedure must define the external metadata-only deletion-register
  schema, reconcile every applicable entry before ordinary access, prove zero
  residual rows, and prove an unrelated control Turnus survives.

## Clean local RED

```text
python manage.py test --noinput --verbosity 1 \
  budo_app.audit_tests.test_audit_security_readiness_command \
  budo_app.audit_tests.test_audit_security_readiness_document
```

Result: expected RED, exit 1. Nine tests ran in 0.012 seconds with nine focused
failures, no errors, no hangs, and a clean Django system check. The seven
command tests stop at the missing repaired schema (`at_rest_decision` is still
unexpected); the two document tests stop at the missing permission-inventory
and external deletion-register procedures.

Python compilation and scoped diff whitespace checks were clean.
