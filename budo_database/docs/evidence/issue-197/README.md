# Issue #197 browser evidence

The executable browser check in `capture.cjs` renders the production React routes
with deterministic populated Admin and Leitung contracts. It checks the approved
Variant C composition at 1440 × 1050 and 390 × 844 before writing screenshots.

Build the production bundle, then run the self-contained check:

```bash
cd budo_database/frontend
npm run build
cd ..
node docs/evidence/issue-197/capture.cjs
```

The script serves the built assets and deterministic API contracts through
Playwright request interception, so it does not need a live Django database or
development server.

## Final verification

- Focused membership/read-contract coverage: 14 frontend tests and 31 backend
  tests passed (4 backend skips).
- Full frontend suite: 34 files, 376 tests passed.
- Full Django suite with isolated in-memory SQLite and a fresh media root: 794
  tests passed, 60 skipped.
- Production `npm run build`: passed and rebuilt the committed static bundle.
- `node docs/evidence/issue-197/capture.cjs`: passed for populated Admin and
  Leitung states at both required viewports.
- `git diff --check`: passed.

The check fails if the continuous desktop master-detail surface, approximately
300px rail, amber request panel, attached identity warning, two-column desktop
member tiles, one-column mobile member flow, horizontal year-grouped mobile
selector, route-specific permissions, or person-specific actions disappear. It
also rejects horizontal page overflow at 390px.

## Reference and actual comparison

| View | Normative Variant C reference | Deterministic production actual |
|---|---|---|
| Desktop | [`../../../frontend/prototypes/team-management-C-desktop.png`](../../../frontend/prototypes/team-management-C-desktop.png) | [`admin--desktop.png`](admin--desktop.png) |
| Mobile | [`../../../frontend/prototypes/team-management-C-mobile.png`](../../../frontend/prototypes/team-management-C-mobile.png) | [`admin--mobile.png`](admin--mobile.png) |
| Leitung desktop | Same approved composition with Leitung capabilities | [`leitung--desktop.png`](leitung--desktop.png) |
| Leitung mobile | Same approved composition with Leitung capabilities | [`leitung--mobile.png`](leitung--mobile.png) |

Computed geometry and surface values are recorded in
[`browser-contracts.json`](browser-contracts.json).
