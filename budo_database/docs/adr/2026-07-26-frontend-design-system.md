# Adopt a shared Tailwind and React frontend design system

- **Status:** Accepted
- **Date:** 2026-07-26
- **Specification:** [GitHub issue #88](https://github.com/dasomji/BuDoBase/issues/88)
- **Developer guide:** [BuDoBase frontend design system](../design-system.md)

## Context

BuDoBase had Tailwind v4 and shadcn/base-ui dependencies, but its pages were
styled through two large global stylesheets. The unlayered legacy stylesheet
overrode Tailwind utilities. Brand colors, buttons, cards, tables, responsive
boundaries, headers, and printing each had multiple incompatible
implementations.

This caused accidental color changes, duplicate DOM ids, page-level horizontal
overflow, inconsistent mobile behavior, hidden mobile actions, and a print path
that could diverge from the React screen's business logic.

This decision implements the frontend direction in spec #88 without changing
the backend architecture or domain behavior. It is consistent with the
[backend rewrite deferral](2026-07-17-backend-rewrite-deferred.md).

## Decision

### Tailwind and tokens

Tailwind utilities are the default styling language for page code. Repeated
interaction and visual patterns live in shared React components based on the
installed shadcn/base-ui primitives.

Semantic colors are defined once in `frontend/src/app.css` through Tailwind
theme tokens. Primary is `#ffdd9b` with `#e6c78b` hover; secondary is
`#a9cfef` with `#8fb8d9` hover. Existing blue surfaces remain distinct.
Success and destructive colors are semantic tokens. Legacy custom properties
with no remaining consumers are removed rather than retained as aliases.

Roboto is self-hosted as variable WOFF2 assets with a metric-adjusted local
fallback. Third-party component CSS is imported into a `vendor` cascade layer
before application components and utilities.

The legacy stylesheet is contained in a named `legacy` cascade layer while
consumers migrate, then removed with the remaining legacy selectors. Dark mode
is not part of this decision.

### Shared components

- The shared Button owns primary, secondary, success, destructive, outline,
  ghost, link, and icon treatments. Header actions remain available on mobile
  as accessible icon buttons.
- Card owns collapse state, keyboard behavior, mobile default collapse, and the
  non-toggling header action area. Solid cards omit the plus/minus icon;
  transparent cards retain it.
- Tables have two tiers. Table primitives plus `TableScroll` serve
  editable/custom/in-card/print tables. `DataTable` serves read-only grids with
  the shared column, sorting, child-name filtering, scrolling, sticky, and
  low-priority-column behavior. Tables do not receive generated ids.
- Header owns the responsive control order and keeps publishing its measured
  height through `--app-header-height`.

### Responsive boundary

Application mobile behavior changes below 901px; desktop behavior starts at
901px. React code uses the shared reactive `useIsMobile()` hook. Styling uses
the matching 900/901 boundary. Older breakpoints are transitional legacy code,
not choices for new work.

The specification planned a registered custom Tailwind variant for this
boundary. The shipped implementation instead uses Tailwind arbitrary variants,
`max-[900px]:...` and `min-[901px]:...`, and does not register a named mobile
variant. This is an implementation deviation, not a second breakpoint: both
forms match the same 900/901 boundary.

### Printing

React is the only application print architecture. Every route loads the app
stylesheet for all media. The global print fallback removes application chrome,
expands cards, and prints the cleaned-up React screen in black on white.

A bespoke paper layout is a hidden React print section rendered from the same
page data and business logic. Its shared Button calls `window.print()`. A
separate React route is reserved for a genuinely different document with its
own data contract or workflow.

Server-body injection, the hidden legacy print root, Bootstrap-for-print, a
duplicate legacy stylesheet link, and runtime stylesheet-media changes are not
permitted.

### Verification

Component and page behavior is tested through rendered DOM, roles, ARIA,
visible text, and user events. CSS cascade, overflow, responsive appearance,
and preserved print layouts are verified in browser QA rather than class-list
unit tests.

## Consequences

- New UI has one documented path for colors, actions, expandable surfaces,
  data tables, mobile behavior, and printing.
- Brand changes can be made at the semantic token layer without rewriting page
  markup.
- Screen and print output share React data and business logic, reducing drift.
- Wide tables scroll inside their own boundary and may hide explicitly
  low-priority columns on mobile.
- The final contract step removed the legacy stylesheet, its cascade layer,
  dead UI assets, old responsive breakpoints, and unconsumed legacy
  custom-property aliases. New work uses semantic tokens directly.
- A bespoke print document still needs manual print-preview evidence because
  paper pagination and browser layout are not unit-test behavior.

## Rejected alternatives

- Continue styling pages with unlayered global element and id selectors.
- Create one all-purpose table component for editable, custom, and print grids.
- Render mobile tables as card stacks.
- Maintain a separate server-rendered print DOM beside React.
- Hide actions on mobile.
- Add dark mode as part of this refactor.
