# Issue #93 browser QA

Issue #93 introduces styled table primitives and the read-only `DataTable`,
migrates the existing shared table call sites, and adopts the sticky,
two-axis-scrolling configuration on the All Kids directory.

## Automated verification

- `cd frontend && npm run test -- --run src/components.test.jsx
  src/domains/kids.test.jsx src/domains/allocation.test.jsx
  src/domains/attendance.test.jsx src/domains/focuses.test.jsx
  src/domains/places.test.jsx src/domains/reports.test.jsx
  src/domains/maintenance.test.jsx`: 8 files, 71 tests passed.
- `cd frontend && npm run test`: 24 files, 241 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.
- Source scanning confirms there are no remaining `#kids-table` or
  `:has(#kids-table)` selectors, and `SearchTable` remains only as a
  compatibility alias for `DataTable`.

## Browser verification

The production bundle was served on `127.0.0.1:8014` using only the local
`.artifacts/design-system-review.sqlite3` database through explicit
`DJANGO_SETTINGS_MODULE` and `DATABASE_URL` overrides.

At the 1280 × 900 desktop viewport:

- the document width remained 1280 px;
- the table scroll wrapper measured 984 px client width by 2698 px scroll
  width, proving horizontal overflow stayed inside the component;
- the wrapper measured 720 px client height by 4085 px scroll height, proving
  the All Kids vertical scroll boundary;
- the header and first body cell both computed to `position: sticky`;
- the rendered React `DataTable` had no DOM id.

At the 390 × 844 mobile viewport:

- the document and viewport widths both remained 390 px;
- the table wrapper measured 350 px client width by 731 px scroll width;
- low-priority columns computed to `display: none`, while Name, Familie, Alter,
  SWP 1, SWP 2, Ernährung, Medikamente, and Gesundheitliches remained visible.

The affected route was recaptured at both viewports and for print:

- [`all-kids--desktop.png`](all-kids--desktop.png)
- [`all-kids--mobile.png`](all-kids--mobile.png)
- [`all-kids--print.png`](all-kids--print.png)
- [`report.json`](report.json)

The same captures update the All Kids entries in
[`../design-system-refactor/review.html`](../design-system-refactor/review.html).
The full review manifest report was preserved. The server was stopped after
capture, and no review-database data was changed.
