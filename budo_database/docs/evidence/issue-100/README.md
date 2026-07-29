# Issue #100 browser QA

Issue #100 removes the legacy stylesheet/cascade layer and the unreferenced
JavaScript and template fragments that belonged to the pre-React interface.
The remaining screen and print contracts now live in the design-system bundle.

## Review environment

The production frontend was built and served on exact port `127.0.0.1:8019`
with development settings and only the dedicated local SQLite database:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////tmp/budobase-ticket100/budo_database/.artifacts/design-system-review.sqlite3
```

No shared or remote database was used.

## Browser and print verification

- [`report.json`](report.json) records 56 successful desktop/mobile captures
  across all 28 routes in the holistic review manifest.
- [`overflow-report.json`](overflow-report.json) records all 27 authenticated
  routes at a 390 px viewport. None has document-level horizontal overflow.
- The five print paths have both PDF and page-one PNG evidence: dashboard, All
  Kids, SWP allocation, Happy Cleaning number list, and kitchen.
- The Happy Cleaning station-todo contract also has a dedicated seven-page PDF
  and page-one PNG; every station page contains visible print content.
- The SWP and Happy Cleaning bespoke print layouts retain their verified
  left-aligned, full-width compositions. The All Kids table retains its dense
  print treatment and fits the complete `Anmerkungen` header.
- The matching holistic evidence in
  [`../design-system-refactor/after/`](../design-system-refactor/after/) was
  regenerated from the same final build.

## Bundle and static collection

The generated CSS bundle changed from 137,382 bytes (29,791 gzip) to 115,147
bytes (24,949 gzip). The JavaScript bundle changed from 991,008 bytes (297,916
gzip) to 990,674 bytes (297,770 gzip).

`python manage.py collectstatic --clear --noinput` copied 180 current assets.
The removed stylesheet and named legacy scripts were absent from the collected
output. Railway still runs `collectstatic --noinput`, and the generated
`staticfiles/` directory remains ignored.

## Automated verification

- `cd frontend && npm run test`: 24 files, 249 tests passed.
- `cd frontend && npm run build`: passed.
- `python manage.py test budo_app.test_react_frontend`: 19 tests passed.
- `python manage.py check`: passed.
- `python manage.py test`: 296 tests ran successfully; 284 passed and 12
  skipped.

The captures can be reproduced with
[`../design-system-refactor/capture.cjs`](../design-system-refactor/capture.cjs)
and `CAPTURE_DIR=docs/evidence/issue-100`. Mobile overflow can be repeated with:

```text
BASE_URL=http://127.0.0.1:8019 node docs/evidence/issue-100/check-overflow.cjs
```
