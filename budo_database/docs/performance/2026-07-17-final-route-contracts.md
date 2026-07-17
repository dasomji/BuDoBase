# Final route-contract integration evidence

Date: 2026-07-17

This is the final evidence for removing authenticated `GET /api/app-data/`.
The legacy endpoint, its compatibility serializers, the frontend fallback
mode, and the migration-only route flags have been removed. Public pages load
only `/api/bootstrap/`; every authenticated application route loads bootstrap
plus its declared `/api/route-data/<contract>/` response.

## Measurement method

Measurements used Django's authenticated test client, development settings,
SQLite, and deterministic in-memory media storage. The small and realistic
fixtures are the same shapes as the recorded legacy baseline: 3/48 Kinder,
2/8 Schwerpunkte, 2/10 Teamer, and 1/6 Auslagerorte. Each SQL value is the
median of five local samples. SQL time is informational and is not a CI wall-
clock limit.

The historical realistic combined response was 125,495 bytes, 70 queries, and
3.285 ms median SQL time. A final initial page load consists of the realistic
bootstrap response plus one focused route response:

| Initial page | Bootstrap + route bytes | Reduction | Queries | Small → realistic growth | Median SQL time | SQL reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dashboard | 22,167 | 82.3% | 17 | 0 | 1.093 ms | 66.7% |
| Kinder directory | 19,174 | 84.7% | 13 | 0 | 0.811 ms | 75.3% |
| Kind detail | 4,927 | 96.1% | 15 | 0 | 0.728 ms | 77.8% |
| Schwerpunkteinteilung | 10,230 | 91.8% | 15 | 0 | 0.856 ms | 73.9% |
| Auslagerort detail | 4,159 | 96.7% | 14 | 0 | 0.628 ms | 80.9% |

The realistic bootstrap itself measured 3,674 bytes and 8 queries. Its query
count, and every representative focused route's query count, remained
constant when the fixture grew. The response-byte comparisons remain guarded
against the frozen 125,495-byte legacy measurement in each domain performance
suite; domain suites also retain their own upper query budgets and growth
guards.

## Privacy and security result

The authenticated HTTP contract suites assert active-Turnus isolation,
cross-Turnus detail denial, authentication requirements, and route allow-lists.
Health, social-security, emergency-contact, notes, and money history remain
absent from routes that do not render them. Public bootstrap responses contain
only authentication state, CSRF, and messages, and public/unknown frontend
routes never issue a protected route-data request. The removed URL returns 404
for both public and authenticated clients.

## Mutation refresh audit

| Mutation class | Current examples | Refresh behavior |
| --- | --- | --- |
| Ordinary inline JSON | Pfand; Schwerpunkt choice/assignment; Freunde; Zugabreise toggle/note | Current route contract only |
| Ordinary in-place REST form | Kind note/money; Auslagerort note; Teamer accounting | Current route contract only |
| Shell/search affecting | Profil/Turnus change; Kind, Schwerpunkt, or Auslagerort searchable-label forms | Existing full-page redirect, which naturally reloads bootstrap and the destination contract |

The frontend refresh helper still has an explicit `shellAffecting` path and its
Vitest coverage proves that bootstrap is refreshed only when that declaration
is true. Domain integration tests prove representative ordinary mutations do
not request bootstrap or unrelated route data.

## Manual visual evidence audit

The available July 8 desktop/mobile screenshot sets and manifests under
`/tmp/budobase-react-frontend-*` were inspected for dashboard, Kind detail,
Schwerpunkteinteilung, Serienbrief, and Kindergesamtzahl structure. They show
the established desktop columns, mobile stacking/navigation, and standalone
layouts, but they predate the route-contract ticket wave and their rendered
content does not match the current branch closely enough to serve as a final
pixel baseline. No current-branch print screenshot or PDF baseline was
available. Current source/tests confirm the standalone route declarations,
mobile breakpoint behavior, screenshot-related layout structure, and print
fallback middleware remain unchanged; this removal ticket changes no CSS or
route renderer.
