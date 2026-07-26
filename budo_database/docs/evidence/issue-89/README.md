# Issue #89 browser QA

Issue #89 puts the imported Django stylesheet in the named `legacy` cascade
layer. The layer order is:

1. Tailwind theme
2. Tailwind base
3. legacy
4. Tailwind components
5. Tailwind utilities

This keeps Tailwind Preflight below the legacy stylesheet during the
transition while allowing component and utility rules to override legacy
selectors.

## Automated verification

- `cd frontend && npm run test`: 24 files, 239 tests passed.
- `cd frontend && npm run build`: passed.
- The production CSS contains the named layers in the required order.
- `git diff --check`: passed.

## Browser verification

The app was built and served on `127.0.0.1:8010` using only
`.artifacts/design-system-review.sqlite3`. The capture manifest completed with
HTTP 200 for all 56 desktop/mobile routes. Five print PDFs were also captured.

The frozen before set and the issue #89 after set are available in
[`../design-system-refactor/review.html`](../design-system-refactor/review.html).
The sweep corrected three cascade-transition regressions before the final
capture:

- Tailwind Preflight initially outranked legacy element rules; the explicit
  layer order now places `legacy` after `base`.
- The legacy `#map` height had previously won by selector specificity; a
  temporary unlayered compatibility rule preserves the 70vh map height.
- The Happy Cleaning number-list print page explicitly retains its white paper
  background.

The final targeted recaptures confirm the mobile Happy Cleaning assignment
header, desktop map heights, and Happy Cleaning number-list print layout match
the frozen reference.

The server was stopped after capture. No review-database data was changed.
