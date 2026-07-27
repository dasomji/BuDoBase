# Issue #121 browser QA

Issue #121 makes the burger, search toggle, and route-owned page action use
shared Button sizes. At and below 900px, all three controls follow the design
system's 32px circular header-action contract with the same 16px glyph size.
The old ID-based width, height, padding, radius, and SVG sizing rules are not
part of the rendering path.

## Automated verification

- `cd frontend && npm run test`: 25 files, 256 tests passed.
- `cd frontend && npm run build`: passed and rebuilt
  `budo_app/static/frontend/`.
- `git diff --check`: passed.

The shared component test renders the actual responsive page-action pattern,
keeps all three controls accessible and interactive, and verifies the mobile
order without taking a utility-class snapshot.

## Browser verification

The rebuilt production bundle was served on `127.0.0.1:8021` with development
settings and an explicit SQLite URL. To ensure login/session activity could
not alter the shared review database, QA used the disposable copy
`/tmp/budobase-issue-121.9HLuev/review.sqlite3`, copied from
`.artifacts/design-system-review.sqlite3`.

At a 390×844 mobile viewport, the Küche header returned HTTP 200. Computed
browser geometry confirmed that the Drucken page action, search toggle, and
burger were each exactly 32×32px, circular, and contained a 16×16px glyph.
The same run clicked the page action, expanded search, and opened the mobile
sidebar successfully.

The executable rendering assertions and capture steps are in
[`capture-header-controls.cjs`](capture-header-controls.cjs). Machine-readable
observations are in [`browser-contracts.json`](browser-contracts.json), and the
rendered header is shown in
[`kitchen-header-controls--390px.png`](kitchen-header-controls--390px.png).
