# #166 browser integration repairs

Date: 2026-07-31

Real session/browser verification found two integration gaps after the core and
race suites were green.

## CSRF/session JSON body

A tailnet browser POST reproduced `RawPostDataException` because DRF session
authentication's CSRF check consumed the request stream before the view read
the raw JSON body. A CSRF-enforced session regression test captured the RED.
The endpoint-specific session authentication now caches the untouched body
before normal CSRF enforcement.

- New CSRF tracer: 1/1 passed.
- Decoder, endpoint, and race regression selection: 44 passed, with eight
  PostgreSQL-only cases skipped in that SQLite run.
- Real browser POST subsequently committed and redirected successfully.

## Post-navigation success notification

The first real successful save redirected correctly but lost the in-memory
React toast during the full-page navigation. A session/API/bootstrap RED test
proved zero post-navigation messages. Successful new `updated` and `no_change`
commands now queue one generic Django success message; exact replay does not
queue another.

- Producer endpoint plus bootstrap: 13/13 passed.
- Kid-edit, App, and toast selection: 51/51 passed.
- Real tailnet browser save redirected to the refreshed synthetic detail and
  displayed exactly one success toast.

Both messages and tests use generic or synthetic content only. No value is
placed in a URL, message, or browser persistence.
