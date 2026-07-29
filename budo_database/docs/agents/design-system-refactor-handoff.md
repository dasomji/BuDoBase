# Handoff: Design-System Refactor (Spec #88, Tickets #89–#100)

You are the orchestrating agent for the Tailwind design-system refactor. The plan is fully decided
and ticketed — do not re-litigate decisions; they were settled with the maintainer in a grilling
session and are recorded in the spec. Your job is to drive the tickets to done using subagents,
and to keep the before/after review page current so the maintainer can visually verify each step.

## Source of truth

- **Spec:** GitHub issue [#88](https://github.com/dasomji/BuDoBase/issues/88) — problem, decisions, testing seams, out-of-scope.
- **Tickets:** #89–#100 on `dasomji/BuDoBase`, each self-contained with acceptance criteria and `Blocked by` references.
- **Before-state reference:** commit `98d6f48` on `main`.

## Dependency graph — work the frontier

| Ticket | Blocked by |
|---|---|
| #89 legacy stylesheet into cascade layer | — |
| #90 brand tokens in Tailwind theme | #89 |
| #91 rebranded Button + first adoptions | #90 |
| #92 Card action area + unified collapse | #90 |
| #93 table primitives + DataTable (All Kids) | #90 |
| #94 header reorder + mobile icon actions | #91 |
| #95 print fallback + delete legacy print machinery | #89 |
| #96 Happy Cleaning Einteilung migration | #91 #92 #93 |
| #97 HC overview/year/station detail migration | #91 #92 #93 |
| #98 long-tail domain page migrations | #91 #92 #93 #94 |
| #99 design-system guide + ADR | #91 #92 #93 #94 #95 |
| #100 contract: delete legacy stylesheet + cleanup | #95 #96 #97 #98 |

Rules of engagement:

- **One ticket per subagent, fresh context each.** The ticket bodies are written to be self-sufficient; point the subagent at the ticket and this handoff.
- **#89 lands alone** before anything else, followed by a full visual QA sweep (it flips a few
  specificity outcomes — see pitfalls). Do not batch it with #90.
- After #89, `#90 → (#91 | #92 | #93)` fan out; #95 can run in parallel with all component work.
- One reviewable PR per ticket, referencing its issue. Do not close or modify #88 manually.
- Verify before declaring done: `cd frontend && npm run test` (vitest), `npm run build`
  (bundle goes to `budo_app/static/frontend/`), plus the screenshot workflow below for anything visual.

## Key facts and pitfalls (from the codebase audit)

- **The cascade problem (#89):** `frontend/src/app.css` line 2 imports
  `budo_app/static/stylesheet.css` with no `layer()` — unlayered CSS beats all Tailwind layers.
  Wrap it as `layer(legacy)`. Note: rules written directly in `app.css` are ALSO unlayered; they
  keep beating utilities until each page migrates — that's expected during the transition.
- **Token trap (#90):** `--primary` in the current `:root` block is stock shadcn near-black
  (`oklch(0.205 0 0)`). Never move an element to `bg-primary` before #90 lands. Brand values:
  primary `#ffdd9b` / hover `#e6c78b`; secondary is a NEW color `#a9cfef` / hover `#8fb8d9`
  (the "chip blue" the maintainer chose — the existing chips are actually translucent white over
  blue rows; there is no existing token for it). `var(--light-blue)` at `app.css` ~line 1651 is
  referenced but undefined — fix with the new secondary token.
- **Card (#92):** `frontend/src/components.jsx` `Card` already has `headerAction` and
  `showToggleIcon` props — the work is defaults + visuals, not a rewrite. Today it reads a private
  `(max-width: 759px)` matchMedia once at mount; replace with the shared `useIsMobile()`
  (`frontend/src/hooks/use-mobile.js`, 901px) and make it reactive. Transparent cards
  (`className="transparent"`: MapCard, focus week tables, HC year) KEEP the +/− icon.
- **Tables (#93):** the All Kids scroll behavior depends on `stylesheet.css`'s
  `.table-container:has(#kids-table)` rule, and `SearchTable` defaults to `id="kids-table"` at
  8 call sites (3 on the focus dashboard alone — duplicate DOM ids). The HC assignment table
  hardcodes `min-width: 60rem` relaxed only <640px via a JS-applied class. All of that is replaced
  by the tier-1 scroll wrapper.
- **Breakpoints:** 600/639/759/900/1024px all exist today. The single boundary is **901px**
  (`useIsMobile`). Retire the others as pages migrate.
- **Header (#94):** `Header` in `components.jsx` writes `--app-header-height` onto the root
  element via ResizeObserver; several layouts consume it — preserve that contract. The kitchen
  print button is currently hidden <900px by `#headerbutton:has(.kitchen-print-button)` — the new
  rule is: actions are never hidden, they become icon buttons.
- **Print (#95):** `budo_app/middleware.py` injects the legacy Django body into
  `#legacy-print-root`; `budo_app/templates/react_app.html` loads Bootstrap 5.3 from CDN
  (print-only) and `stylesheet.css` a second time for print; only three routes are whitelisted as
  React print pages. `happyCleaning.jsx` (~line 460) flips the stylesheet link's `media` at
  runtime to print station to-dos — all of this dies in #95. The three bespoke print outputs
  (kitchen, HC number list/to-dos, SWP-Einteilung) must be pixel-equivalent before/after.
- **Discovered orphan (not in any ticket):** the React `/audit` route has NO Django URL — the SPA
  uses full page loads (`window.location.assign`), so the audit page is unreachable in production.
  File it as a separate issue (`needs-triage`); do not silently fix it inside a refactor ticket.
- **Danger:** the repo `.env` points `DATABASE_URL` at a REMOTE Neon Postgres. Never run servers,
  captures, or QA against it. Always override `DATABASE_URL` to the local review sqlite (below).

## Screenshot / review-page workflow

The workflow lives in `docs/evidence/design-system-refactor/`:

- `review.html` — the maintainer's verification page. Open it locally (no server needed). Tabs for
  Desktop / Mobile / Print; each page shows **before** and **after** side by side; clicking a shot
  opens a lightbox where B/A keys flicker between the two states. It resolves images by the
  filename contract `before/<slug>--<viewport>.png` and `after/<slug>--<viewport>.png`.
- `capture.cjs` — Playwright capture script. Slugs in it MUST stay in sync with the `MANIFEST`
  in `review.html`.
- `before/` and `after/` contain generated local capture artifacts and are ignored by Git. The
  frozen local `before/` set was captured at commit `98d6f48` (56 screen shots + 5 print PDFs
  converted to PNG). Preserve that local set and do not re-capture it.

To capture the **after** set (repeat after each visually-affecting ticket lands, at minimum after
#92, #94, #96, #97, #98, and before closing #100):

```bash
# 1. Serve the app against the dedicated review DB (never the .env Postgres):
DJANGO_SETTINGS_MODULE=budo_database.settings.development \
DATABASE_URL="sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3" \
python3 manage.py runserver 127.0.0.1:8010 --noreload

# 2. Build the frontend first so the server serves the new bundle:
cd frontend && npm run build && cd ..

# 3. Capture (all pages, or CAPTURE_ONLY=slug1,slug2 for the pages a ticket touched):
BASE_URL=http://127.0.0.1:8010 HC_ID=1 \
CAPTURE_DIR=docs/evidence/design-system-refactor/after \
node docs/evidence/design-system-refactor/capture.cjs

# 4. Convert print PDFs to page-1 PNGs:
cd docs/evidence/design-system-refactor/after && python3 -c "import fitz,glob
[fitz.open(p)[0].get_pixmap(dpi=100).save(p.replace('.pdf','.png')) for p in glob.glob('*--print.pdf')]"
```

About the review DB (`.artifacts/design-system-review.sqlite3`):

- It is a migrated copy of `.artifacts/baseline.sqlite3` (migrated through `0082`), seeded with
  Happy Cleaning data: event id **1** ("Happy Cleaning 1", turnus T2-2023) with 7 stations and
  37 assignments (3 excused). QA login: username in `.artifacts/baseline/username.txt`
  (`pi_screenshot`), password `baseline-only-password`.
- **Do not change its data** — before/after comparability depends on identical content. If a
  migration added during the refactor requires `manage.py migrate`, run it against this DB too
  and note it in the evidence README.
- If the DB is ever lost, recreate it: copy `baseline.sqlite3`, migrate, and re-run the seed
  (a Happy Cleaning event with 7 stations/37 assignments — see git history of this handoff), then
  re-capture BOTH before (from a `98d6f48` checkout + rebuilt frontend) and after.

Also capture targeted QA evidence per ticket as the tickets require (the `docs/evidence/issue-NN/`
pattern) — `review.html` is for the maintainer's holistic pass, not a substitute for per-ticket
acceptance evidence.

## Definition of done (overall)

- All 12 tickets closed; `stylesheet.css` gone; no unlayered legacy CSS left in the bundle.
- `review.html` fully populated: every page has before + after at desktop/mobile (and print where
  flagged), captured against the same review DB.
- Frontend tests green; the three bespoke print outputs unchanged; no page overflows at 390px.
- Design-system guide + ADR merged (#99) and linked from the agent docs index.
