# #164-05 repair 02 RED — summary-only explorer compatibility

Date: 2026-07-31

Scope: frontend tests and evidence only. No production, structured reveal,
detail fetch, staging, commit, or push change was made.

## Contract regression

The audit explorer fixture now matches the exact list API boundary:

- no event has a full `details` member;
- legacy events contain only the value-free `sensitive` and
  `available_fields` summary;
- `kid.edit` contains only schema/version/result, changed paths, and the
  sensitive marker;
- each event supplies its own `details_url`, including an explicitly selected
  Turnus query where present.

The focused rendering regression requires a bounded presentation: only the
count of sensitive kid changed paths, safe legacy field names, no raw kid path
names or full values, and keyboard/screen-reader discoverable links whose href
is exactly the server-provided `details_url`. It does not fetch or reveal the
detail payload.

## Focused Vitest RED

The worktree temporarily linked its ignored `frontend/node_modules` path to the
canonical repository's existing dependency installation. The link was removed
immediately after each run.

```text
npm --prefix frontend test -- --run src/domains/audit.test.jsx
```

After correcting a duplicate actor label in the two-row fixture, the clean
result was expected RED, exit 1: six tests ran in 523 ms, five controls passed,
and the single new compatibility test failed because the current table renders
neither `details_summary` nor an accessible `details_url` link. There were no
test errors or hangs.

Scoped diff whitespace checks were clean, and the temporary dependency link is
absent.
