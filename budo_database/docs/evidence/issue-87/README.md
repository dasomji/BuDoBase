# Happy Cleaning integrated hardening evidence (#87)

Captured on 2026-07-25 from commit baseline `61ff487` plus the #87
hardening changes.

## Performance budgets

The regression fixtures use 48 children, 12 stations, eight tasks per
station, and a historical copy batch of 12 stations × eight tasks.

| Flow | Query budget | Response-byte budget |
| --- | ---: | ---: |
| Initial overview | 7 | 24,000 |
| Explicit active-year load | 7 | 24,000 |
| Historical-year expansion | 6 | 16,000 |
| Station detail | 12 | 32,000 |
| Assignment snapshot | 12 | 64,000 |
| Copy conflict preview | 18 | 8,000 |
| Copy commit | 90 | 56,000 |

The representative SQLite copy commit measured 78 queries and 50,945
response bytes. Read-query growth remains at most one query as children,
stations, and tasks grow; adding the large historical year adds zero queries
and zero bytes to the initial overview.

These contracts live in
`budo_app/happy_cleaning_tests/test_performance.py`.

## Automated interaction and correctness evidence

- Overview sorting, history expansion, local detail open/switch/close, focus
  restoration, create/edit/delete eligibility, dirty guard, and both copy
  entry points:
  `frontend/src/domains/happyCleaning.test.jsx` and
  `frontend/src/domains/happyCleaningStationDetail.test.jsx`.
- Copy conflict-free success, multi-match resolution, overwrite-disabled
  reason, append provenance, separate, and skip:
  `frontend/src/domains/happyCleaning.test.jsx`,
  `frontend/src/domains/happyCleaningStationDetail.test.jsx`, and
  `budo_app/happy_cleaning_tests/test_copy_stations.py`.
- Different-task success, same-task stale, structural stale, stale copy
  preview, overbooking confirmation races, reconnect refresh, and
  transaction/audit rollback:
  `budo_app/happy_cleaning_tests/test_command_races.py`,
  `test_todo_operations.py`, `test_edit_station.py`,
  `test_copy_stations.py`, and the corresponding frontend tests.
- Historical response and rendered-DOM redaction, exact overbooking, and
  retired URL/static-route absence:
  `budo_app/happy_cleaning_tests/test_contracts.py`,
  `frontend/src/domains/happyCleaning.test.jsx`,
  `frontend/src/domains/happyCleaningStationDetail.test.jsx`, and
  `frontend/src/routes.test.jsx`.

## Browser evidence

Chrome was connected to a migrated, isolated SQLite database served by
Django's ASGI development server. The fixture contains active and historical
Turni, two copy targets, an exactly overbooked station, and canonical document
tasks. The retained browser session could not be authenticated as that fixture
user reliably: the bounded login attempt navigated away from the inspected
target, and the resulting capture was correctly rejected during visual
inspection because it showed the login page.

No screenshot is presented as product evidence for this run. Responsive and
workflow states are covered by the automated DOM and accessibility tests
above; they were not replaced with synthetic screenshots.

## Environment qualification

Final local verification:

- Django, isolated SQLite: 292 tests passed, 12 PostgreSQL/Redis-specific
  tests skipped; `manage.py check` reported no issues.
- Vitest: 24 files, 229 tests passed.
- Vite production build: passed (2,074 modules transformed); the existing
  advisory reports the 978.50 kB minified application chunk.

PostgreSQL independent-connection race tests skip on SQLite by design. The
configured Neon hostname was not resolvable from the sandbox, so this run
could not independently re-execute the PostgreSQL-only race cases.
