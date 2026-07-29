# Issue #98 browser QA

Issue #98 migrates the long-tail application screens to shared components and
utility layouts. The browser pass covers the dashboard, profiles, attendance,
reports, focuses and meals, SWP allocation, kitchen, places, and maintenance
entry points represented by the seeded review database.

## Review environment

The production frontend was built and served on `127.0.0.1:8018` with the
development settings and only the dedicated local SQLite database:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////tmp/budobase-ticket98/budo_database/budo_database/.artifacts/design-system-review.sqlite3
```

No shared or remote database was used. The capture did not run migrations or
write domain data.

## Browser verification

- [`report.json`](report.json) contains 44 successful desktop/mobile captures
  across the 22 affected seeded routes.
- [`overflow-report.json`](overflow-report.json) records the same 22 routes at
  390 px. Every route has a 390 px document width and no document-level
  horizontal overflow.
- The complete holistic review manifest at
  [`../design-system-refactor/after/report.json`](../design-system-refactor/after/report.json)
  was regenerated and contains all 56 records.
- The dedicated Küche output is preserved in
  [`kitchen--print.pdf`](kitchen--print.pdf) and
  [`kitchen--print.png`](kitchen--print.png).
- The SWP allocation output is preserved in
  [`swp-einteilung-w1--print.pdf`](swp-einteilung-w1--print.pdf) and
  [`swp-einteilung-w1--print.png`](swp-einteilung-w1--print.png), including its
  single decorative BuDo illustration behind the visible list content.

The audit React page cannot currently be reached through Django because the
repository has no `/audit` URL mapping. That pre-existing route boundary is
tracked separately as issue #101; its shared table-scroll contract is covered
by `audit.test.jsx`. First-aid entries are exercised through the dashboard
capture, while the photo gallery's navigation, dismissal, and accessibility
contracts are covered by `firstAidGallery.test.jsx`; the review database does
not contain a seeded first-aid photo suitable for an honest gallery capture.

## Reproduction

The route capture uses
[`../design-system-refactor/capture.cjs`](../design-system-refactor/capture.cjs)
with `CAPTURE_DIR=docs/evidence/issue-98` and the 22 issue route slugs. Mobile
overflow can be repeated with:

```text
node docs/evidence/issue-98/check-overflow.cjs
```

The source verification is:

```text
cd frontend
npm test
npm run build
```

The server was stopped after the final capture.
