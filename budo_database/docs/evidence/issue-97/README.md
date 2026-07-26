# Issue #97 browser QA

Issue #97 migrates the Happy Cleaning overview, year cards, number list,
station detail, editor, and copy dialogs to shared Button, Card, and table
components plus Tailwind utilities. The station-detail stylesheet and obsolete
overview/detail rules are removed; the assignment page remains untouched.

## Automated verification

- `cd frontend && npm run test -- --run src/domains/happyCleaning.test.jsx
  src/domains/happyCleaningStationDetail.test.jsx
  src/happyCleaningSync.test.js`: 3 files, 35 tests passed.
- `cd frontend && npm run test`: 24 files, 248 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.

The rendered-DOM tests preserve sorting, lazy year loading, station selection,
task toggling, editor commands, dirty-navigation handling, copy flows,
realtime refresh behavior, and the number-list content. They also verify the
shared table/Button DOM contracts. A print contract protects the established
number-list gradient, typography, spacing, and table sizing from the legacy
print-only stylesheet that is still loaded on this pre-#95 base branch.

## Browser verification

The production bundle was served on exact port `127.0.0.1:8016` with explicit
local-only settings:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

The route capture report records HTTP 200 at desktop and mobile widths for the
overview and number list. The focused station-detail contract confirms:

- desktop document width 1280 px at a 1280 px viewport;
- mobile document width 390 px at a 390 px viewport, in read and edit modes;
- desktop station-table overflow stays inside its 440 px scroll wrapper
  (676 px scroll width);
- mobile detail starts exactly below the measured 66 px header;
- the transparent year Card retains its `−` indicator;
- close and save actions expose the shared Button DOM contract.

The desktop split-grid overflow found during the first pass was fixed before
the final captures. The number-list print was compared with the verified #95
reference; its bespoke radial gradient, bold headings, spacing, 11 pt table
text, and cell treatment are preserved while the screen uses shared table
primitives.

Evidence:

- [`happy-cleaning--desktop.png`](happy-cleaning--desktop.png)
- [`happy-cleaning--mobile.png`](happy-cleaning--mobile.png)
- [`hc-station-detail--desktop.png`](hc-station-detail--desktop.png)
- [`hc-station-detail--mobile.png`](hc-station-detail--mobile.png)
- [`hc-station-editor--desktop.png`](hc-station-editor--desktop.png)
- [`hc-station-editor--mobile.png`](hc-station-editor--mobile.png)
- [`hc-nummernliste--desktop.png`](hc-nummernliste--desktop.png)
- [`hc-nummernliste--mobile.png`](hc-nummernliste--mobile.png)
- [`hc-nummernliste--print.png`](hc-nummernliste--print.png)
- [`hc-nummernliste--print.pdf`](hc-nummernliste--print.pdf)
- [`browser-contracts.json`](browser-contracts.json)
- [`report.json`](report.json)

The final overview and number-list captures also update the matching `after/`
entries in
[`../design-system-refactor/review.html`](../design-system-refactor/review.html).
Only authentication/session metadata changed during QA; Happy Cleaning domain
records were not mutated. The port-8016 server was stopped after capture.
