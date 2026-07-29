# Issue #124 browser evidence

Captured on 2026-07-27 from the rebuilt production frontend bundle on
`agent/design-system-review-124`.

## Automated verification

- `cd frontend && npm run test`: 26 files, 263 tests passed.
- `cd frontend && npm run build`: passed and rebuilt
  `budo_app/static/frontend/`.
- `DATABASE_URL='sqlite:///:memory:' python -Wd manage.py test`: 297 tests
  passed, 12 skipped.
- `git diff --check`: passed.

The rendered-DOM tests cover the actual interaction seams without utility-class
snapshots:

- keyboard navigation changes the Einteilung search option's
  `aria-selected` state;
- a 116-character contact email remains a complete accessible `mailto:` link;
- the focus assignment table renders the child's age value through the shared
  number-cell convention; and
- the unsaved-changes surface retains a named level-two dialog heading.

## Environment and data safety

- Browser: headless Chrome through the required CDP browser workflow and the
  executable Playwright assertions in
  [`capture-regressions.cjs`](capture-regressions.cjs).
- Server:
  `DJANGO_SETTINGS_MODULE=budo_database.settings.development` at
  `http://127.0.0.1:8024`.
- Database: disposable copy
  `/tmp/budobase-issue-124.SYejVE/review.sqlite3`, copied from the local review
  SQLite before the server started.
- The source and copy initially had the same SHA-256:
  `2300c2f07ab0909ca924a76869a4e521035555c39b1e25894c561e45aabac381`.
- Only the disposable copy's `pi_screenshot` email was changed, to the
  116-character address shown in the mobile capture. Login sessions also
  changed only that copy.
- After QA, the shared
  `.artifacts/design-system-review.sqlite3` still had SHA-256
  `2300c2f07ab0909ca924a76869a4e521035555c39b1e25894c561e45aabac381`.

## Browser contracts

Machine-readable computed styles and geometry are in
[`browser-contracts.json`](browser-contracts.json).

| Regression | Verified contract |
|---|---|
| Number cells | Eight sampled All Kids ages computed `text-align: right` and shared the exact same right edge. The review fixture has no children assigned to its focus, so `/schwerpunkt/1/` shows the age header plus its genuine empty state; the rendered focus test supplies an assigned child and exercises the same shared number-cell path. |
| Station close action | The header has no toggle icon, `.card-header-action` computes `margin-right: 0px`, and the close action ends exactly one normal 24px header padding inset from the card edge. |
| Dirty-dialog heading | The `h2` computes `margin-top: 0px`; its top gap is exactly the popup's 24px padding, with no additional heading margin. |
| Long email | At 390×844, the document and body remain exactly 390px wide. The link computes `overflow-wrap: anywhere`; Card and Card content both compute `min-width: 0px`. |
| Child-name visibility | The toggle remains reachable at 639px, 640px, 800px, and 900px without introducing a second responsive breakpoint. |
| Active search option | A real rendered ghost Button's shared class contract was exercised with `aria-selected="true"`: background stayed `rgb(169, 207, 239)` before and during hover. The page test drives the actual child search from inactive to keyboard-active. The review DB's redacted child names do not produce live search results, so the browser assertion uses a clone of a rendered ghost Button rather than altering review data. |
| Station row headers | At 639, 640, 800, and 900px they compute `white-space: normal`, use each row's surface/stripe background, and differ from the nowrap accent background reserved for column headers. |

## Captures

| File | Contract shown |
|---|---|
| [`all-kids-number-cells--desktop.png`](all-kids-number-cells--desktop.png) | Right-aligned ages in the shared directory table |
| [`station-detail-header--desktop.png`](station-detail-header--desktop.png) | Close action restored to the no-toggle Card edge position |
| [`dirty-dialog--desktop.png`](dirty-dialog--desktop.png) | Dialog heading starts at the popup's normal padding |
| [`team-long-email--390px.png`](team-long-email--390px.png) | Long email wraps inside the expanded 390px Team card |
| [`assignment-table--800px.png`](assignment-table--800px.png) | Child-name toggle is reachable and station row headers use row chrome at tablet width |
