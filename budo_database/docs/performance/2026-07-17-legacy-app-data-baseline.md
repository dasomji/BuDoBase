# Legacy application-data baseline

Date: 2026-07-17

This is the pre-migration baseline for authenticated `GET /api/app-data/`.
It characterizes the existing combined response; it is not a performance goal
for focused contracts.

## Fixture profiles

Both profiles use one active Turnus and deterministic in-memory Django media
storage, so image URLs do not contain volatile S3 signatures.

| Profile | Kinder | Schwerpunkte | Teamer | Auslagerorte |
| --- | ---: | ---: | ---: | ---: |
| Small | 3 | 2 | 2 | 1 |
| Realistic | 48 | 8 | 10 | 6 |

Every Kind has one assignment, one Schwerpunkt choice, two notes, and two
Taschengeld entries. Each Teamer has one accounting entry. Each Auslagerort
has one note and one image. Schwerpunkte include their generated meal rows.

## Measurements

The measurements were made through Django's authenticated test client using
SQLite and the development settings. SQL time measures database execution
only with Django's connection execute wrapper; it does not include request,
serialization, or network time. The SQL values below are medians of five local
samples and are informational, never CI limits.

| Profile | Response bytes | Queries | Median SQL time |
| --- | ---: | ---: | ---: |
| Small | 10,756 | 44 | 2.090 ms |
| Realistic | 125,495 | 70 | 3.285 ms |

Growing from the small to realistic fixture adds 26 queries and 114,739 bytes.
The response becomes about 11.7 times larger. The query increase is expected
characterization evidence for the legacy serializer, whose Profil and
Schwerpunkt relation access can bypass prefetched relations.

## Regression seam

`budo_app.read_contracts.measurement.measure_http_get` records status, response
bytes, query count, and SQL execution time for an HTTP GET. The accompanying
`QueryBudgetAssertions` mixin provides upper-bound and small-to-large fixture
growth assertions. It deliberately does not provide exact-query or wall-clock
assertions.

The characterization test keeps broad ceilings of 100 queries for the
realistic legacy fixture and growth of at most 40 queries. Focused contracts
should set their own materially smaller budgets in their exclusive domain test
packages.
