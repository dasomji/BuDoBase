# Issue #96 browser QA

Issue #96 migrates the Happy Cleaning Einteilung page to Tailwind utilities
and the shared Button, Card, and table primitives. The assignment table now
lives inside the shared scroll boundary at every viewport, low-priority
columns use the shared table contract, and child pills use the secondary-blue
token. The page-specific `60rem` table width, private 639 px viewport hook,
mobile table class, and obsolete assignment CSS were removed.

## Automated verification

- `cd frontend && npm run test -- --run src/domains/happyCleaningAssignment.test.jsx src/domains/happyCleaning.test.jsx`:
  2 files, 39 tests passed.
- `cd frontend && npm run test`: 24 files, 249 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.

The domain-page suite preserves rendered behavior for child search, assignment
and moves, Entschuldigt, counters, number editing, realtime write gating, and
station details. Its migrated-structure check verifies shared table slots,
the internal scroll boundary, low-priority columns, the 901 px mobile
boundary, and the existing hide/show child-name interaction without asserting
visual class strings.

## Browser verification

The production bundle was served on `127.0.0.1:8015` with the explicit local
review database override:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

The exact 320 px lower bound, phone (390×844), tablet (768×1024), and desktop
(1280×900) checks all returned HTTP 200. At every width, document and body
scroll widths exactly matched their client widths, so the page had no
horizontal overflow. The table was a shared `data-slot="table"` inside a
`data-slot="table-scroll"` element whose computed horizontal overflow was
`auto`; the wrapper remained bounded to the page at 320 px, phone, and tablet
widths. The rendered child pills resolved to the secondary token
`rgb(169, 207, 239)`.

A non-mutating browser interaction selected an existing child pill and
confirmed that the shared selected-child Card and search state updated. The
normal station targets remained number-gated for that child while
`Entschuldigt` remained available, matching the assignment contract. No
review-database data was changed.

Machine-readable observations are in
[`browser-contracts.json`](browser-contracts.json).

Screenshots:

- [`hc-assignment--mobile.png`](hc-assignment--mobile.png)
- [`hc-assignment--tablet.png`](hc-assignment--tablet.png)
- [`hc-assignment--desktop.png`](hc-assignment--desktop.png)
- [`report.json`](report.json)

The matching desktop and mobile images under
`docs/evidence/design-system-refactor/after/` were refreshed from the same
capture.
