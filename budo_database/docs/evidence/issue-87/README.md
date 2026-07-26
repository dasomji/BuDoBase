# Happy Cleaning integrated hardening evidence (#87)

Captured on 2026-07-26 from commit baseline `61ff487` plus the #87
hardening and integration changes.

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
tasks. The authenticated captures were visually inspected after capture:

| Screenshot | Viewport | Evidence |
| --- | --- | --- |
| [`desktop-split-overbooked.png`](desktop-split-overbooked.png) | 1280 × 937 | The overview and local detail remain visible in the 50/50 desktop split. The selected Speisesaal shows the exact `1 überbelegt` state, assigned children, task progress, and station actions. |
| [`mobile-fullscreen-overbooked.png`](mobile-fullscreen-overbooked.png) | 390 × 844 | The same station occupies the mobile content area below the fixed application header. `Zur Liste`, the station title, exact overbooking state, children, and tasks remain visible without being covered by the header. |
| [`mobile-stacked-conflict.png`](mobile-stacked-conflict.png) | 390 × 844 | A station-copy preview shows the target, unresolved-group count, source-to-target candidate, and stacked overwrite/append/separate/skip choices. Target-dependent choices are disabled until a candidate is selected and no destructive choice is preselected. |
| [`desktop-minimal-editor.png`](desktop-minimal-editor.png) | 1280 × 937 | The local desktop editor keeps the overview in context and exposes only station metadata, responsible-person selection, stable task rows, save, and guarded navigation controls; no rich-text toolbar is present. |

Together these captures cover the required responsive split/full-screen
layouts, exact overbooking communication, copy-conflict decision surface, and
minimal station editor. The automated interaction evidence above covers
create/edit/delete eligibility, conflict-free copy success, multi-candidate
selection, append provenance, separate/skip behavior, keyboard focus
restoration, and dirty-navigation decisions that are temporal or
authorization-dependent and cannot be established by a single still image.

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
