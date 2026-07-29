# Issue #117 browser evidence

Captured on 2026-07-27 from the production frontend bundle built from
`7c69820` plus the uncommitted issue #117 changes.

## Environment and data safety

- Browser: headless Chrome, `390 × 844`, device pixel ratio `1`.
- Server: `DJANGO_SETTINGS_MODULE=budo_database.settings.development` at
  `http://127.0.0.1:8010`.
- Database: disposable copy
  `/tmp/budobase-issue-117.sLKXSF/review.sqlite3`, copied from the local review
  SQLite before the server started.
- The source and copy initially had the same SHA-256:
  `2300c2f07ab0909ca924a76869a4e521035555c39b1e25894c561e45aabac381`.
- After all QA writes, the shared
  `.artifacts/design-system-review.sqlite3` still had SHA-256
  `2300c2f07ab0909ca924a76869a4e521035555c39b1e25894c561e45aabac381`.
  Only the disposable copy changed.

## Captures

| File | Contract shown |
|---|---|
| `delete-confirmation-dialog--mobile.png` | Block label above a full-width, immediately visible confirmation input |
| `delete-confirmation-ready--mobile.png` | Exact confirmation text entered and the final delete action enabled |
| `birthdays-note--mobile.png` | Kindergeburtstage Notiz inputs visibly styled in table rows |
| `pocket-money-amount--mobile.png` | Taschengeld amount input visibly styled in the fixed interaction bar |
| `allocation-select--mobile.png` | SWP-Einteilung native selects visibly styled in table rows |
| `station-copy-target--mobile.png` | Stationen-kopieren target select with label, border, padding, radius, and background |
| `station-copy-conflict--mobile.png` | Conflict target select using the same shared contract |

Every inspected `Input` and `NativeSelect` reported the same computed control
contract: `1px solid rgb(221, 221, 221)` border, `rgb(255, 255, 255)`
background, `4px 10px` padding, and `10px` border radius. The delete input was
`32px` high, occupied the dialog content width, was associated with its visible
label, and received autofocus.

## Behavioral QA

The destructive flow was exercised end to end on the disposable database:

1. Created a deletable `Happy Cleaning 2`.
2. Opened its delete dialog; the final action was disabled.
3. Entered `Happy Cleaning 2`; the final action became enabled.
4. Activated the final delete action; the dialog closed and the event
   disappeared from the overview.

The station-copy workflow was also exercised on the disposable copy. Seven
stations were copied into a new target event, then one was copied again to
produce a real conflict. Both the initial target select and the conflict target
select retained the shared native-control appearance and behavior.
