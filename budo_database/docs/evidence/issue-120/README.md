# Issue #120 browser evidence

Captured on 2026-07-27 from the production frontend bundle built from
`d364d90` plus the uncommitted issue #120 changes.

## Environment and data safety

- Browser: headless Chrome, `390 × 844`, device pixel ratio `1`.
- Server: `DJANGO_SETTINGS_MODULE=budo_database.settings.development` at
  `http://127.0.0.1:8010`.
- Database: disposable copy
  `/tmp/budobase-issue-120.op9D4E/review.sqlite3`, copied from the local review
  SQLite before the server started.
- The shared review database retained SHA-256
  `2300c2f07ab0909ca924a76869a4e521035555c39b1e25894c561e45aabac381`
  after QA. Only the disposable copy was edited: child 21 received the QA-only
  name `QA Mobile` and present state so the assignment audit could complete.

## Captures

| File | Contract shown |
|---|---|
| `einteilung-mobile-selected.png` | Selecting the QA child immediately exposes the expanded child panel, visible minus toggle, and number form |
| `einteilung-mobile-reselected.png` | After assigning the child from Speisesaal to Entschuldigt and selecting it again, the panel and number form are immediately reachable again |
| `transparent-card-mobile.png` | The open `Woche 1` transparent card renders its table flush with the card edge at 390 px |

[`browser-metrics.json`](browser-metrics.json) records the corresponding
computed and behavioral checks. Both initial selection and re-selection
reported `aria-expanded="true"`, a visible `−` toggle, non-inert content, and
a rendered number input. The assignment request completed between the two
captures.

The transparent card reported `0px` inline padding on both sides; its card and
content left edges both measured `20px`. The selected solid-card header
reported `filter: none` at rest and `filter: brightness(1.1)` under pointer
hover, confirming visible hover feedback is applied only through the
collapsible `.card-toggle` seam.
