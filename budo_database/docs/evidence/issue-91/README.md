# Issue #91 browser QA

Issue #91 rebrands the shared shadcn Button with the BuDoBase theme tokens and
adopts it for the Taschengeld actions plus the kitchen and Happy Cleaning print
actions. Other buttons remain on their existing legacy styling until their
ticketed migrations.

## Automated verification

- `cd frontend && npm run test -- src/components.test.jsx src/domains/kids.test.jsx src/domains/kitchen.test.jsx src/domains/happyCleaning.test.jsx`:
  4 files, 60 tests passed.
- `cd frontend && npm run test`: 24 files, 244 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.

The shared-component tests exercise rendered-DOM behavior only: named button
variants, native and link disabled behavior, a real named link, and a labeled
icon action whose SVG is hidden from the accessibility tree. They do not assert
class strings or colors.

## Browser verification

The production frontend was built and served on `127.0.0.1:8010` using only
the dedicated local review database:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

All eight desktop/mobile route requests in [`report.json`](report.json)
returned HTTP 200. The browser pass confirmed:

- the Taschengeld controls remain named `Abbuchen` and `Aufladen`, retain their
  form behavior, and render with the semantic success green and destructive red;
- the Happy Cleaning To-Do action renders with the supporting secondary blue,
  while the kitchen and number-list print actions demonstrate the primary
  orange Button treatment;
- the Happy Cleaning mobile print action remains named `Drucken` and renders
  as the established circular icon affordance;
- the kitchen mobile capture preserves the current hidden-header-action
  behavior; making header actions visible and reordering them is intentionally
  reserved for issue #94;
- no affected mobile capture overflows the 390 px viewport;
- the review database was not modified.

The focused Taschengeld captures switch the existing interaction bar into its
money mode:

- [`kid-detail-money--desktop.png`](kid-detail-money--desktop.png)
- [`kid-detail-money--mobile.png`](kid-detail-money--mobile.png)

The route-level desktop/mobile evidence is:

- [`kid-detail--desktop.png`](kid-detail--desktop.png) /
  [`kid-detail--mobile.png`](kid-detail--mobile.png)
- [`happy-cleaning--desktop.png`](happy-cleaning--desktop.png) /
  [`happy-cleaning--mobile.png`](happy-cleaning--mobile.png)
- [`hc-nummernliste--desktop.png`](hc-nummernliste--desktop.png) /
  [`hc-nummernliste--mobile.png`](hc-nummernliste--mobile.png)
- [`kitchen--desktop.png`](kitchen--desktop.png) /
  [`kitchen--mobile.png`](kitchen--mobile.png)

The unchanged print outputs were also recorded as
[`hc-nummernliste--print.pdf`](hc-nummernliste--print.pdf) and
[`kitchen--print.pdf`](kitchen--print.pdf). The same eight route screenshots
update the `after/` side of
[`../design-system-refactor/review.html`](../design-system-refactor/review.html).
The server was stopped after capture.
