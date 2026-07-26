# Issue #92 browser QA

Issue #92 updates the shared Card contract: solid cards use the header action
area without a toggle indicator, transparent cards retain their live `+`/`−`
indicator, and uncontrolled cards react to the shared 901 px mobile boundary.
The existing blue surfaces and reduced-motion behavior remain, while solid
cards use a soft layered shadow.

## Automated verification

- `cd frontend && npm run test -- src/components.test.jsx src/domains/focuses.test.jsx src/domains/happyCleaning.test.jsx src/domains/happyCleaningStationDetail.test.jsx src/domains/dashboard.test.jsx`:
  5 files, 66 tests passed.
- `cd frontend && npm run test`: 24 files, 242 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.

The shared-component tests cover the rendered-DOM contract without visual
class-string assertions: solid and transparent indicators, header-action event
isolation, header click and keyboard toggling, `aria-expanded`, `aria-hidden`,
`inert`, and reactive behavior at 900/901 px.

## Browser verification

The production bundle was served on `127.0.0.1:8012` with the explicit local
review database override:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

Production-browser checks confirmed:

- a solid dashboard card has no indicator and resolves the two soft shadow
  layers to `0 4px 12px` and `0 1px 3.2px`;
- the same card is expanded at 901 px, collapses with an inert body at 900 px,
  and expands again when returned to 901 px;
- Space collapses and Enter expands the focused header while keeping its ARIA
  state and body accessibility state synchronized;
- the transparent Map card retains `−`, and clicking its Woche 2 header action
  changes the pressed week without collapsing the card;
- with reduced motion enabled, the Card body computes to zero-duration/no
  transition.

The machine-readable observations are in
[`browser-contracts.json`](browser-contracts.json).

Representative screenshots:

- [`dashboard--desktop.png`](dashboard--desktop.png)
- [`dashboard--mobile.png`](dashboard--mobile.png)
- [`swp-dashboard--desktop.png`](swp-dashboard--desktop.png)
- [`swp-dashboard--mobile.png`](swp-dashboard--mobile.png)
- [`happy-cleaning--desktop.png`](happy-cleaning--desktop.png)
- [`happy-cleaning--mobile.png`](happy-cleaning--mobile.png)
- [`report.json`](report.json)

The complete design-system `after/` set was refreshed as required: 56
desktop/mobile captures across 28 routes, with zero non-OK responses. Existing
print captures were regenerated from the same unchanged review database. The
server was stopped after capture, and no review-database data was changed.
