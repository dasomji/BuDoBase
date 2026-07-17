# Backend rewrite deferred until after the 2026 summer camps

- **Status:** Accepted
- **Date:** 2026-07-17
- **Review:** After the 2026 summer-camp season
- **Near-term priority:** Make the existing Django/React application reliable, fast, observable, and well tested

## Decision

Do not rewrite the backend before the 2026 summer camps.

Continue improving the current Django application. Revisit a TypeScript backend after the camps, when there is enough time to characterize existing behavior and migrate in vertical slices without putting camp operations at risk.

The current preferred direction for that later rewrite is:

- React and Vite for the web frontend
- Express 5 as an explicit HTTP backend
- Better Auth
- PostgreSQL and Drizzle
- Zod 4 at every external input seam
- Socket.IO for the few pages that need realtime updates
- private S3-compatible object storage, likely Railway Buckets

This is a direction, not an irreversible stack commitment. Re-evaluate the current maturity of TanStack Start, Express alternatives, Better Auth, and offline-sync tooling when the work resumes.

## Why the rewrite is still reasonable later

The strongest reasons are maintainability and future product shape:

- End-to-end types make refactoring and AI-assisted maintenance safer.
- Zod schemas can be shared across HTTP, WebSocket, import, and mobile interfaces.
- Web, backend, and a possible React Native client can share TypeScript packages.
- Node has strong WebSocket and mobile-client ecosystems.
- The product roadmap includes collaborative editing and eventually offline-capable native apps.
- The existing frontend is already React, reducing the eventual language split.

The rewrite should **not** be justified primarily by expected runtime performance. Query shape, response size, caching, and database access patterns will matter more than Python versus Node for this application.

## Why it is deferred

A rewrite would replace more than a language. It would replace or reproduce:

- Django authentication, sessions, permissions, and CSRF handling
- Django forms and validation behavior
- ORM mappings and a history of 68 migrations
- model methods and business rules
- admin functionality
- file and image handling
- Excel import/export edge cases
- deployment and operational behavior

Doing this immediately would create a long period with two implementations and a high risk of subtle behavior regressions during the most operationally important part of the year.

## Why Express is currently preferred over TanStack Start

Express fits the current application and longer-term clients more directly:

- The existing Vite/React frontend can remain in place during the backend migration.
- The same explicit HTTP interface can serve the web app and native mobile apps.
- Socket.IO can attach directly to the Node HTTP server.
- Uploads, S3 streams, Excel jobs, and background workers fit a conventional long-running Node process.
- The backend remains independent from the web rendering framework.
- Django and Express can coexist while routes migrate incrementally.

TanStack Start remains a valid option if, at review time, the team values its typed router, loaders, server rendering, and server functions enough to accept tighter coupling to the web application. Its server functions are primarily intended for the Start application; mobile clients would still need stable server routes. As of this decision, TanStack Start is release-candidate software, while Express is mature and intentionally minimal.

Express must not become the architecture. Route and Socket.IO handlers should only authenticate, validate, invoke an application module, and translate the result. Domain behavior should live behind small interfaces that can be called by HTTP routes, WebSocket handlers, jobs, tests, and future sync endpoints.

## Realtime conclusion

Django can support WebSockets today through Django Channels, so realtime is not by itself a reason to rewrite.

For the future `Schwerpunkteinteilung`, start with a server-authoritative design rather than a CRDT:

1. Load a versioned allocation snapshot.
2. Send a command such as `assignKidToFocus` with the expected version.
3. Validate authorization and invariants on the server.
4. Commit the change in a database transaction.
5. Acknowledge the writer and broadcast the committed event to the room.
6. Refresh the affected snapshot after a version conflict or reconnect.

WebSockets are transport, not conflict resolution. PostgreSQL remains the source of truth. Multiple application replicas will require shared pub/sub, such as Redis, rather than process-local broadcasts.

## Excel conclusion

Excel support should not block the rewrite.

The current import is concentrated in `budo_app/excelProcessor.py`; the export in `budo_app/updateExcel.py` is considerably smaller. SheetJS and ExcelJS cover the required XLSX reading and writing capabilities, but formula results, date serials, styles, blank values, and malformed cells can differ from pandas/openpyxl.

Before porting Excel processing:

1. Collect representative real workbooks.
2. Snapshot the normalized output and errors from the Python importer.
3. Build a small TypeScript proof with SheetJS or ExcelJS.
4. Compare every imported field and error case.
5. Open generated exports in Excel and LibreOffice.

If parity is not good enough, retain the Python importer temporarily behind an `importWorkbook` interface and run it as a worker. Do not spread spreadsheet-library details through route handlers.

## Authentication migration warning

The current app is username-oriented and stores Django password hashes. Better Auth is email-oriented and uses scrypt by default.

At migration time, audit whether every account has a unique valid email, then choose deliberately between:

- a forced password reset, likely simplest for a small user population; or
- a temporary verifier for legacy Django hashes followed by rehashing.

Do not try to keep Django and Better Auth simultaneously authoritative for the same accounts for an extended period.

## Mobile and offline conclusion

Native apps should never connect directly to PostgreSQL. They should synchronize through authenticated backend interfaces.

Before mobile development, syncable records will need stable client-generatable identifiers, versions, timestamps, tombstones where deletion must synchronize, mutation idempotency keys, incremental change retrieval, and an explicit conflict policy per domain. Money, attendance, and focus assignments should not silently use generic last-write-wins behavior.

Shared TypeScript and Zod schemas will help, but TypeScript does not provide offline synchronization by itself.

## Migration approach when work resumes

Avoid a big-bang rewrite:

1. Preserve representative workbooks, API responses, screenshots, and domain behavior as characterization tests.
2. Define framework-independent application modules in the current system where practical.
3. Introduce the TypeScript backend alongside Django.
4. Migrate one complete vertical slice at a time, including authorization, validation, persistence, UI integration, and tests.
5. Use `Schwerpunkteinteilung` as a likely first TypeScript/realtime slice.
6. Give database migrations one clear owner during every stage.
7. Migrate authentication at one explicit cutover point.
8. Remove Django only after all routes, scheduled work, imports, exports, storage operations, and administrative workflows have replacements.

## Resume checklist

When this decision is reviewed after the camps:

- Confirm that the product roadmap still includes realtime collaboration and native offline clients.
- Re-evaluate TanStack Start's release status and deployment model.
- Re-evaluate Express, Fastify, and Hono based on current ecosystem maturity.
- Verify Better Auth's migration and React Native support.
- Run the TypeScript Excel parity spike.
- Inventory Django admin workflows and permissions that need replacements.
- Decide the user/password migration strategy.
- Decide whether the existing PostgreSQL schema will be mapped first or redesigned through staged migrations.
- Agree on API versioning and mobile sync requirements before implementing mobile endpoints.
- Establish performance and correctness baselines before moving the first slice.

## Near-term Django performance direction

The most important near-term improvement is to stop returning one complete application data graph for every page.

`GET /api/app-data/` currently serializes children, private health and contact fields, notes, money transactions, focus groups, team members, places, images, totals, and activity regardless of the current route. Every successful mutation then calls the same endpoint again. This increases database work, serialization time, JSON transfer, browser parsing, memory use, and exposure of sensitive fields.

The Django improvement plan is:

1. Measure query count, SQL time, response time, and response bytes for representative routes.
2. Split common shell data from route-specific data.
3. Return only fields required by each route.
4. Refetch or patch only the affected route resource after a mutation.
5. Remove query patterns that bypass prefetched relations.
6. Paginate or cap unbounded activity lists.
7. Add shared caching only after query and payload work is measured.

This work is not throwaway. The resulting route contracts and application interfaces can become the specification for a later TypeScript backend.

## References available at decision time

- [TanStack Start server functions](https://tanstack.com/start/latest/docs/framework/react/guide/server-functions)
- [TanStack Start hosting](https://tanstack.com/start/latest/docs/framework/react/guide/hosting)
- [Express middleware](https://expressjs.com/en/5x/guide/using-middleware/)
- [Better Auth Express integration](https://better-auth.com/docs/integrations/express)
- [Better Auth Expo integration](https://better-auth.com/docs/integrations/expo)
- [Django Channels](https://channels.readthedocs.io/en/stable/)
- [Railway Buckets](https://docs.railway.com/storage-buckets)
- [SheetJS API](https://docs.sheetjs.com/docs/api/)
- [ExcelJS](https://github.com/exceljs/exceljs)
