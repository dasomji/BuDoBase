# Dashboard read contract

Date: 2026-07-17

`GET /api/route-data/dashboard/` returns the active Turnus projection used by
the dashboard cards. Kinder, team, profile, Schwerpunkt, financial, note, and
transaction values are allow-listed to the fields rendered by that page.

## Activity bound and continuation

The initial response contains independent `notes` and `transactions` pages.
Each page is limited to 20 items and reports `items`, `next_cursor`,
`has_more`, and `limit`. Older activity is requested with:

```text
GET /api/route-data/dashboard/?activity=notes&cursor=<next_cursor>
GET /api/route-data/dashboard/?activity=transactions&cursor=<next_cursor>
```

Both streams use descending `(date_added, id)` keyset order. The opaque cursor
contains the final tuple from the previous page. This tie-breaker makes the
order deterministic when timestamps match, while keyset continuation prevents
newer inserts from shifting older pages and causing duplicates or skipped
records.

## Local measurement

Measurements use the same deterministic SQLite/in-memory-storage fixture as
the legacy application-data baseline. SQL time is informational; query and
payload assertions in CI are upper bounds.

| Response | Kinder | Activity per stream | Bytes | Queries | SQL time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Focused, small | 3 | 6 | 3,063 | 9 | 0.953 ms |
| Focused, realistic | 48 | 20 | 18,575 | 9 | 0.670 ms |
| Legacy combined, realistic | 48 | all 96 | 125,495 | 70 | 5.309 ms |

The realistic initial focused response is 85.2% smaller than the legacy
combined response. Query count remains 9 as Kinder, team members, notes, and
transactions grow from the small to realistic fixture.
