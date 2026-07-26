# Issue #94 browser QA

Issue #94 restructures the shared application header without changing the
route-action or sidebar-sheet contracts. Desktop headers render the sidebar
trigger, title, global search, and action in that order. Below the shared
901 px breakpoint they render the title, labeled icon action, search toggle,
and burger before the collapsible global-search row.

## Automated verification

- `cd frontend && npm run test -- src/components.test.jsx src/routes.test.jsx
  src/navigation.test.jsx src/domains/kitchen.test.jsx
  src/domains/happyCleaning.test.jsx src/domains/allocation.test.jsx
  src/domains/focuses.test.jsx src/domains/places.test.jsx
  src/domains/reports.test.jsx src/domains/dashboard.test.jsx
  src/App.test.jsx`: 11 files, 147 tests passed.
- `cd frontend && npm run test`: 24 files, 254 tests passed.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.

The shared-component tests exercise the agreed rendered-DOM seam with the
existing mocked viewport pattern. They cover both header orders, labeled icon
actions, expanding and collapsing mobile search, the existing full-viewport
sidebar sheet, unchanged global-search keyboard behavior, and publication and
cleanup of `--app-header-height`. The Küche route test also clicks the mobile
printer action and observes `window.print()`.

## Browser verification

The production frontend was built and served on `127.0.0.1:8010` using only
the dedicated local review database:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

All 16 desktop/mobile requests in [`report.json`](report.json) returned HTTP
200. No migration or domain-data write was run. The browser pass confirmed:

- desktop order is sidebar trigger → title → search → action;
- mobile order is title → action → search → burger;
- pages without an action retain the compact title → search → burger layout;
- every existing route header action remains visible on mobile as a labeled
  32 px shared Button/icon affordance;
- the Küche printer action is visible on mobile with the primary brand
  treatment, while its established print document remains available;
- long titles truncate without displacing the mobile controls;
- the global review page's selected `after/` screenshots were refreshed, while
  its complete 56-entry report was preserved after verifying that all 16
  refreshed entries match.

Representative route evidence:

- [`dashboard--desktop.png`](dashboard--desktop.png) /
  [`dashboard--mobile.png`](dashboard--mobile.png)
- [`kindergeburtstage--desktop.png`](kindergeburtstage--desktop.png) /
  [`kindergeburtstage--mobile.png`](kindergeburtstage--mobile.png)
- [`swp-dashboard--desktop.png`](swp-dashboard--desktop.png) /
  [`swp-dashboard--mobile.png`](swp-dashboard--mobile.png)
- [`swp-einteilung-w1--desktop.png`](swp-einteilung-w1--desktop.png) /
  [`swp-einteilung-w1--mobile.png`](swp-einteilung-w1--mobile.png)
- [`happy-cleaning--desktop.png`](happy-cleaning--desktop.png) /
  [`happy-cleaning--mobile.png`](happy-cleaning--mobile.png)
- [`hc-nummernliste--desktop.png`](hc-nummernliste--desktop.png) /
  [`hc-nummernliste--mobile.png`](hc-nummernliste--mobile.png)
- [`kitchen--desktop.png`](kitchen--desktop.png) /
  [`kitchen--mobile.png`](kitchen--mobile.png)
- [`auslagerorte--desktop.png`](auslagerorte--desktop.png) /
  [`auslagerorte--mobile.png`](auslagerorte--mobile.png)

The Küche print evidence is [`kitchen--print.pdf`](kitchen--print.pdf). The
server was stopped after capture.
