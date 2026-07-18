# Happy Cleaning print evidence (#44)

Captured locally on 2026-07-18 from an authenticated, active-Turnus fixture
containing 84 children (48 numbered and present, 12 numberless and present,
24 absent).

## Browser evidence

- [Desktop screen](print-page-desktop.png)
- [Mobile screen](print-page-mobile.png)
- [Print-media first page](print-preview-first-page.png)
- [A4 PDF](happy-cleaning-number-list.pdf)

The browser DOM contained the three titled sections with 48, 12, and 24
rows. The first numbered values were `1..8`, and the seeded private health
marker was absent from the complete DOM. At a 390 px mobile viewport the
document scroll width was 390 px after correcting inherited no-wrap styling.

Under emulated print media, computed styles showed:

- React root: `display: block`;
- legacy print root, application header, and print actions: `display: none`;
- print rows: `break-inside: avoid`;
- black text on a white background.

## Automated validation

- Full Django/SQLite suite: passed (exit 0).
- Happy Cleaning Django suite: 64 passed, 8 environment-gated skips.
- Full frontend suite: 163 passed across 21 files.
- Focused route/App/Happy Cleaning frontend suite: 58 passed.
- Vite production build and `manage.py check`: passed.
- Production settings check with an ASGI-compatible Redis URL: passed.
- Missing and malformed `REDIS_URL` production checks failed clearly with
  `ImproperlyConfigured`, as intended.
- Focused contracts stayed below their existing query/payload budgets and
  their exact allow-list tests passed.

PostgreSQL race and Redis cross-process tests could not run locally because
the services/binaries were unavailable and Docker daemon access was denied.
`.github/workflows/django-postgresql.yml` provisions PostgreSQL 16 and Redis 7,
sets `DATABASE_URL` and `REDIS_URL`, and runs the full Django suite. Railway
starts `daphne ... budo_database.asgi:application`; production settings require
and validate `REDIS_URL` without logging credentials.
