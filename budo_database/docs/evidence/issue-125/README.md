# Issue #125 verification

Verified from the `agent/design-system-review-125` working tree based on
`4eed438`.

## Dead-code audit

The source and rebuilt bundles contain none of the retired hooks:

- CSS selectors: `react-actions`, `deposit-actions`, and
  `#right-column:has(#ort-detail-info)`.
- Shared component hooks: `flex-container`, `table-container`, `data-table`,
  `table-header`, `table_row`, `text-cell`, and `open-icon`.
- Page hooks: `kitchen-print-button`, `happy-cleaning-delete-backdrop`,
  `happy-cleaning-delete-dialog`, `happy-cleaning-overview-list`,
  `happy-cleaning-overview-layout`, `happy-cleaning-overview-split`,
  `happy-cleaning-overview-detail`, `happy-cleaning-todo-print-ready`,
  `happy-cleaning-conflict-summary`, `happy-cleaning-station-detail-card`, and
  `happy-cleaning-station-facts`.
- The `SearchTable` export and the no-op Happy Cleaning `Printer` `size` prop.
- The unconsumed legacy color aliases and the unused `--z-toggle-button` and
  `--z-map-modal` tokens.

The remaining `happy-cleaning-*` classes all own screen or print rules.
`data-slot="table-header"` is an intentional semantic attribute and is not the
removed `.table-header` class.

## Cascade audit

The source declares the order
`theme, base, vendor, components, utilities`. Leaflet is imported with
`layer(vendor)`, before application components and Tailwind utilities.

The production bundle contains one occurrence each of the `vendor`,
`components`, and `utilities` layers. Their first byte offsets are 9,877,
24,986, and 45,666 respectively. It contains no `components.components`
sublayer. The shared print block remains outside every named layer in source,
so its author rules continue to outrank all layered screen utilities.

## Font provenance and network audit

Roboto comes from `@fontsource-variable/roboto` 5.3.0, authored by Google,
packaged by Fontsource, and licensed under OFL-1.1. The dependency and registry
integrity are pinned in `frontend/package-lock.json`.

The production build emits these self-hosted variable WOFF2 files:

| File | SHA-256 |
|---|---|
| `roboto-latin-ext-wght-italic-BdF9m8sc.woff2` | `7f21d061a9de1ea78a858938ff3b8e677869656b10bad470fc6039f8f3daf329` |
| `roboto-latin-ext-wght-normal-DYIxWhlt.woff2` | `cedb374b05a35034cf96db185db4eeb8f8ce49e1a56197673702ff11b5533d6e` |
| `roboto-latin-wght-italic-BZYj8CJm.woff2` | `14f23757c6b41b4b6c0b967ca3fa74ff47a868728158373461c4e6e4b6368f19` |
| `roboto-latin-wght-normal-ccAYIvAh.woff2` | `1404ca348bd75ef836f4dd8b6f2cc719458642d1237c368296b2fc652dca47dc` |

The Django shell, CSS, and JavaScript bundles contain no
`fonts.googleapis.com` or `fonts.gstatic.com` reference.

## Browser spot check

[Desktop Auslagerorte with Leaflet map](places-desktop.png) was captured at
1,440 × 1,000 from `http://127.0.0.1:8015/auslagerorte-list/`. The server used
a disposable copy of the review database at
`/tmp/budobase-125-browser.sqlite3`.

Chrome reported:

- computed body font: `Roboto, "Roboto Fallback", sans-serif`;
- `document.fonts.check("16px Roboto")`: `true`;
- a rendered `.leaflet-container`;
- the local normal Latin WOFF2 as the font resource;
- zero Google Fonts resource entries.

The screenshot confirms the map, table, header, sidebar, and Roboto text render
without an unintended layout change.

## Automated verification

- `cd frontend && npm run test`: 26 files, 263 tests passed.
- `cd frontend && npm run build`: passed; rebuilt `app.css`, `app.js`, and four
  Roboto assets.
- `DATABASE_URL='sqlite:///:memory:' python -Wd manage.py test`: 297 tests
  passed, 12 skipped.
- Django shell/print checks: 27 tests passed.
