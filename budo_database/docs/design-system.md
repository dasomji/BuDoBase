# BuDoBase frontend design system

This guide is the contract for new and migrated React UI. It documents the
shared APIs shipped in `frontend/src` and the decisions recorded in
[the design-system ADR](adr/2026-07-26-frontend-design-system.md).

The legacy global stylesheet has been removed. Prefer Tailwind utilities and
the shared components described here; server-rendered compatibility markup is
not precedent for new work.

## Source locations

- Tokens and shared component styling:
  [`frontend/src/app.css`](../frontend/src/app.css)
- Button:
  [`frontend/src/components/ui/button.jsx`](../frontend/src/components/ui/button.jsx)
- Header, Card, DataTable, and shared layout/data helpers:
  [`frontend/src/components.jsx`](../frontend/src/components.jsx)
- Table primitives:
  [`frontend/src/components/ui/table.jsx`](../frontend/src/components/ui/table.jsx)
- Mobile behavior:
  [`frontend/src/hooks/use-mobile.js`](../frontend/src/hooks/use-mobile.js)
- Shared component behavior tests:
  [`frontend/src/components.test.jsx`](../frontend/src/components.test.jsx)

## Color tokens

`@theme static` in `frontend/src/app.css` is the source of truth. Use semantic
Tailwind utilities such as `bg-primary`, `hover:bg-primary-hover`,
`text-primary-foreground`, and `border-border`; do not repeat these color
literals in component markup.

| Token | Exact value | Intended use |
|---|---:|---|
| `background` | `#ffffff` | App/page background |
| `foreground` | `#373737` | Default text |
| `card` | `rgb(222 240 255 / 70%)` | Translucent blue card surface |
| `card-foreground` | `#373737` | Text on cards |
| `popover` | `#ffffff` | Popover surface |
| `popover-foreground` | `#373737` | Text on popovers |
| `primary` | `#ffdd9b` | Primary actions |
| `primary-hover` | `#e6c78b` | Primary action hover |
| `primary-foreground` | `#373737` | Text/icons on primary |
| `link` | `#373737` | Neutral dark link text on page and card surfaces |
| `secondary` | `#a9cfef` | Supporting actions |
| `secondary-hover` | `#8fb8d9` | Secondary action hover |
| `secondary-foreground` | `#373737` | Text/icons on secondary |
| `muted` | `rgb(183 220 255 / 34%)` | Muted blue surface |
| `muted-foreground` | `#5f6368` | Muted text |
| `accent` | `rgb(179 202 217 / 95%)` | Strong blue chrome/header surface |
| `accent-foreground` | `#373737` | Text on accent |
| `success` | `#54b958` | Success and money-add actions |
| `success-foreground` | `#373737` | Text/icons on success |
| `destructive` | `#b93f3b` | Destructive and money-remove actions |
| `destructive-foreground` | `#ffffff` | Text/icons on destructive |
| `border` | `#dddddd` | Borders |
| `input` | `#686868` | Input borders; shared with `ring` |
| `ring` | `#686868` | Focus rings, including card headers and table sort controls |
| `surface` | `rgb(222 240 255 / 70%)` | General translucent blue surface |
| `surface-solid` | `#def0ff` | Opaque blue surface |
| `surface-subtle` | `rgb(183 220 255 / 34%)` | Subtle blue surface/row |
| `surface-header` | `rgb(179 202 217 / 95%)` | Blue header/table chrome |

The retired legacy color aliases have no consumers and are not part of the
design-system API. Use the semantic tokens above. Dark mode is not part of the
current system.

## Fonts and vendor styles

Roboto is self-hosted as variable WOFF2 assets for normal and italic text,
covering Latin and Latin Extended characters at weights 100–900. The source
files come from the OFL-1.1-licensed `@fontsource-variable/roboto` package;
the local `Roboto Fallback` face adjusts Arial's width and line metrics to
Roboto during font swap. Do not add external font stylesheets, preconnects, or
requests.

Third-party component CSS belongs in a named `vendor` cascade layer before
`components` and `utilities`. Leaflet follows this contract, so an application
utility on a map element wins without selector escalation.

## Button

Import the shared Button directly:

```jsx
import { Button } from '../components/ui/button';
```

`Button` renders a real button by default. Supplying `href` renders an anchor
with the same visual contract. A disabled anchor receives `aria-disabled`,
leaves the tab order, and prevents activation.

The focus treatment is shared by all variants. Variant definitions must never
declare `focus-visible:` classes, because tailwind-merge would drop the base
ring.

```jsx
<Button onClick={save}>Speichern</Button>
<Button variant="secondary" onClick={preview}>Vorschau</Button>
<Button variant="destructive" onClick={remove}>Löschen</Button>
<Button variant="link" href="/profil/">Profil öffnen</Button>
```

Available variants are:

| Variant | Use |
|---|---|
| `default` | Primary orange action; this is the default |
| `secondary` | Supporting blue action |
| `success` | Successful or money-add action |
| `destructive` | Destructive or money-remove action |
| `outline` | Neutral bordered action |
| `ghost` | Low-emphasis action |
| `link` | Link treatment; normally use with `href` |

Available sizes are `default`, `xs`, `sm`, `lg`, `responsive-icon`, `icon`,
`icon-xs`, `icon-sm`, and `icon-lg`. `size="icon"` is the 32px circular icon
action. `size="responsive-icon"` is a text action on desktop and a 32px
circular icon action below 901px. Every icon-only action needs an `aria-label`;
decorative icons must be hidden from assistive technology.

```jsx
<Button size="icon" aria-label="Drucken" onClick={() => window.print()}>
  <Printer aria-hidden="true" />
</Button>
```

Header actions that keep text on desktop and become an icon on mobile use the
shipped responsive label pattern. At the mobile boundary, every icon-only
header action must be a 32px circle—never a square or rounded square. The shared
`size="responsive-icon"` Button variant owns this responsive shape; the
`mobile-icon-action` class only switches the label. Do not recreate or override
its dimensions, padding, or border radius on individual pages.

```jsx
<Button
  className="mobile-icon-action"
  size="responsive-icon"
  type="button"
  aria-label="Drucken"
  onClick={() => window.print()}
>
  <span className="desktop-action-label">Drucken</span>
  <Printer className="mobile-action-label" aria-hidden="true" />
</Button>
```

Use `Button` instead of new `.button` anchors or bare button styling. Keep the
native `type`, form, ARIA, and disabled semantics appropriate to the action.

## Header

`Header` owns the application title, sidebar trigger, global search, optional
route action, responsive control order, and the application-chrome height
contract. Pages do not render a second header. A route declares its optional
action with a `headerAction(data, pageContext)` function:

```jsx
{
  title: 'Auslagerorte',
  headerAction: () => (
    <Button
      className="mobile-icon-action"
      size="responsive-icon"
      href="/auslagerorte/create"
      aria-label="Ort hinzufügen"
    >
      <span className="desktop-action-label">Ort hinzufügen</span>
      <Plus className="mobile-action-label" aria-hidden="true" />
    </Button>
  ),
  render: ({ data }) => <PlacesPage data={data} />,
}
```

`pageContext` supplies `pageState`, `setPageState`, and `mutate` when an action
needs page-owned state or a mutation. Return the action node or `null`; do not
imperatively mount into the header. Authenticated controls render in this order:

| Mode | Control order |
|---|---|
| Desktop (at least 901px) | Sidebar trigger, title, global search, route action |
| Mobile (below 901px) | Title, route action, search toggle, sidebar trigger, global-search region |

The route action is omitted when absent. Unauthenticated headers render only the
logo and title. On mobile, icon-only controls follow the 32px circular Button contract
described above and require accessible names. The search and sidebar controls
use 30px glyphs; route-action glyphs retain the shared Button size so they fit
inside their colored circles. Below 901px, the sidebar menu fills the viewport
width and its primary and nested navigation items use 1.2rem text.

`Header` measures itself on mount, resize, content resize, and search expansion,
then publishes the result as `--app-header-height` on the document root. Sticky
controls and viewport-height layouts consume that property instead of copying a
header height. Header removes the property when it unmounts.

## Error feedback

Field-addressable form validation uses a compact page summary, invalid control
styling, a concrete inline message, `aria-invalid`/`aria-describedby`, and
focus on the first invalid control. Cards containing invalid controls open and
may show an error count in their header. These field errors do not also emit a
generic error toast.

Action-level, transport, and non-field errors continue to use the shared error
toast unless a dedicated recovery flow owns the message. Successful
asynchronous writes that have no sufficiently clear immediate result use the
shared success toast for confirmation. The duplicate-number recovery dialog in
the Happy-Cleaning assignment flow remains an action prompt within that
recovery flow.

Rendered-DOM tests for a form with field-addressable errors cover summary
semantics, inline association, first-invalid focus, Card opening/error counts,
and absence of a duplicate error toast.

## Card

Import `Card` from the shared module:

```jsx
import { Card } from '../components';
```

A Card is an expandable `section` with an `h2` by default. Its whole header is
keyboard- and pointer-operable. On desktop it starts open unless
`initiallyClosed` is true. Below 901px it starts closed, and that default reacts
when the shared mobile state changes.

```jsx
<Card title="Gesundheit">
  <HealthDetails />
</Card>
```

Solid cards intentionally have no plus/minus icon. Transparent cards retain the
icon because their surface does not otherwise make collapsibility obvious:

```jsx
<Card title="Karte" className="transparent">
  <Map />
</Card>
```

Put contextual actions in `headerAction`. The shared Card stops events from
that area from toggling the card.

```jsx
<Card
  title="Woche 1"
  headerAction={<Button href="/swp-einteilung-w1">Kinder einteilen</Button>}
>
  <WeekSummary />
</Card>
```

Put actions that belong at the bottom of the card in `actions`, not in an ad hoc
wrapper inside `children`. Card renders them in a shared wrapping footer with
top padding and end alignment. The footer is hidden when printing.

```jsx
<Card
  title="Woche 1"
  actions={(
    <>
      <Button variant="secondary" onClick={preview}>Vorschau</Button>
      <Button onClick={save}>Speichern</Button>
    </>
  )}
>
  <WeekSummary />
</Card>
```

Card props:

| Prop | Contract |
|---|---|
| `title` | Required visible title and basis of the toggle's accessible name |
| `children` | Expandable content |
| `id`, `className` | Optional DOM id and additional classes |
| `initiallyClosed` | Start closed on desktop too |
| `headerAction` | Contextual action that does not toggle the card |
| `actions` | Bottom actions rendered with shared top padding, wrapping, end alignment, and print hiding |
| `showToggleIcon` | Explicitly override icon visibility |
| `as` | Container element/component; defaults to `section` |
| `headingLevel` | Heading level number; defaults to `2` |
| `expanded` | Controlled expanded state |
| `onExpandedChange` | Controlled-state callback |

Do not build a second collapse state around Card. Use `expanded` and
`onExpandedChange` when another component must control it.

### Responsive card grids

Use `ResponsiveCardGrid` for responsive card collections. Its default Tailwind
grid keeps source order. For dashboards whose cards expand and collapse, pass
`independentColumns`. This variant is a Tailwind container-query layout: it uses
one column below 41rem of available content width, two columns from 41rem, and
three from 62rem. These widths are measured inside the application content area,
so the sidebar is excluded. Cards are distributed left-to-right across stable
columns. Each column stacks independently, so collapsing a card pulls up the
cards below it without leaving gaps beneath cards in neighboring columns. Do not
recreate this distribution at page call sites. Use `maxColumns={2}` for card
collections, such as family lists, that should never grow beyond two columns.

## Shared layout and data helpers

The shared module also exports these load-bearing building blocks. Import them
from `../components` rather than recreating their structure at page call sites.

| Component | Contract |
|---|---|
| `Columns` | Page `<main id="body-container">`; accepts `className` for the page's grid or flow layout |
| `Column` | Detail-column wrapper; accepts `id` and `className` |
| `FieldList` | Renders `[label, value]` pairs and omits null, undefined, and empty values |
| `ResponsiveCardGrid` | Responsive Card collection; use `independentColumns` and `maxColumns` as documented above |
| `RestForm` | CSRF-aware asynchronous `FormData` POST through the shared form-submit endpoint; owns busy state and error toasts |
| `NativeForm` | Schema-driven native GET form or POST form built on `RestForm` and the shared `.form-grid` seam |
| `MapCard` | Transparent expandable Card containing the shared Leaflet map; accepts `places` and an optional `headerAction` |

## Native form controls

Use the shared token-backed controls for standalone text-like inputs, textareas,
and native selects rendered outside `NativeForm`'s `.form-grid` seam:

```jsx
import { Input, NativeSelect, Textarea } from '../components/ui/input';

<label className="grid gap-1 font-medium">
  Ziel
  <NativeSelect name="target">
    <option value="">Bitte wählen</option>
  </NativeSelect>
</label>

<Input name="note" aria-label="Notiz" />
<Textarea className="min-h-[2lh]" name="details" aria-label="Details" />
```

`Input`, `Textarea`, and `NativeSelect` share one visual contract: full width,
visible `border-input` border, rounded corners, compact padding, `bg-popover`
background, foreground/placeholder tokens, and the standard `ring` focus
treatment. The boundary clears 3:1 against the field fill and every supported
surface; `input` and `ring` deliberately share the same color. All three
preserve native form semantics and expose stable `data-slot="input"`,
`data-slot="textarea"`, or `data-slot="native-select"` rendering hooks.
`Textarea` does not set a fixed height; callers own its height constraints.

Use ordinary layout utilities on the associated label or container. Do not
restore global `input`, `select`, or `label` rules and do not recreate the
control border, padding, radius, background, or focus treatment per page.
Checkboxes, radios, file inputs, search widgets, and specialized controls keep
their owning component or page contract.

## Tables: choose one of two tiers

Both tiers share the same blue header, row borders, and horizontal scroll
boundary. Every table should be inside `TableScroll`; scrolling is a container
behavior, never a page-wide minimum width.

Table surfaces are **opaque**, and must stay that way. The page paints a
white-to-grey radial gradient plus a fixed illustration behind every table, so
a translucent row composites over whatever it happens to sit on: the same row
reads at 10.6:1 in the middle of the page and 5.4:1 near the edge, and links
inside it drop below the AA floor. A translucent cell also lets the columns
underneath show through when the first column is pinned during horizontal
scroll. Use `--color-table-row`, `--color-table-row-excused` and
`--color-table-header`; do not tint a row with an alpha utility such as
`bg-white/20`. Rows are a single tint rather than a stripe — the 1px row border
already separates them, and the previous two stripes differed by 1.01:1, which
is invisible.

To mark a row state, set `--table-row-background` from a data attribute on the
row (see `[data-slot="table-row"][data-excused]`) rather than a background
utility on the row element. Only the custom property reaches the pinned first
column, so a utility leaves the sticky cell showing the wrong colour.

### Tier 1: table primitives

Use primitives for editable/form grids, custom interactive grids, small tables
embedded in cards, and print-specific tables. The primitives keep semantic
table markup while leaving cell behavior to the caller.

```jsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components';
import { Input } from '../components/ui/input';

<TableScroll stickyHeader>
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead scope="col">Name</TableHead>
        <TableHead scope="col" data-priority="low">Notiz</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {children.map(child => (
        <TableRow key={child.id}>
          <TableCell>{child.full_name}</TableCell>
          <TableCell data-priority="low">
            <Input aria-label={`Notiz für ${child.full_name}`} />
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</TableScroll>
```

`TableScroll` accepts `stickyHeader`, `stickyFirstColumn`, and
`verticalScroll`. The last option caps the container at `80vh` and enables
vertical scrolling. Its remaining DOM props and `className` pass through.
Mark the same header and body cells with `data-priority="low"` to hide that
column through 900px.

The primitive components pass ordinary table attributes through. Supply
semantic attributes such as `scope`, accessible labels, and form labels at the
call site.

### Tier 2: DataTable

Use `DataTable` for read-only data grids that benefit from shared sorting
and, where appropriate, the existing child-name filter.

```jsx
import { DataTable } from '../components';

const columns = [
  { key: 'name', label: 'Name', render: row => row.full_name },
  { key: 'age', label: 'Alter' },
  {
    key: 'birthday',
    label: 'Geburtstag',
    render: row => formatGermanDate(row.birthday),
    sortValue: row => row.birthday,
  },
  { key: 'note', label: 'Notiz', priority: 'low', sortable: false },
];

<DataTable
  columns={columns}
  rows={children}
  showFilter
  stickyHeader
  stickyFirstColumn
  verticalScroll
/>
```

Each row must have a stable, unique `id`. A column supports:

| Field | Contract |
|---|---|
| `key` | Stable column key and default row property |
| `label` | Header text |
| `render(row)` | Optional rendered cell content |
| `sortValue(row)` | Optional underlying value used for sorting |
| `sortable: false` | Disable the otherwise-default sortable header |
| `priority: "low"` | Hide this column through 900px |
| `className` | Class added to body cells |

`DataTable` accepts `empty` (default `Keine Einträge`), an optional explicit
`id`, `beforeFilter`, and the three `TableScroll` behavior flags. Its shared
controls area provides consistent top spacing below application chrome and
spacing between stacked controls. It never generates a table id.

`showFilter` is not a general full-row search. It filters the first available
value from `row.filterText`, `row.full_name`, or `row.name`, using German
case-insensitive matching. Populate `filterText` when the visible name is
rendered from another shape. Do not expect values in arbitrary columns to
match.

The retired `SearchTable` alias has been removed. Use `DataTable`.

## One mobile boundary

The application has exactly one mobile/tablet boundary:

- Mobile behavior and layout: viewport width below 901px
- Desktop behavior and layout: viewport width at least 901px

For React behavior, always call the shared reactive hook:

```jsx
import { useIsMobile } from '@/hooks/use-mobile';

const mobile = useIsMobile();
```

Do not copy `window.innerWidth`, create another `matchMedia` hook, or use a
private threshold. For CSS, the exact matching queries are
`(max-width: 900px)` and `(min-width: 901px)`. Tailwind arbitrary variants may
express the same boundary as `max-[900px]:...` and `min-[901px]:...`.
Do not use Tailwind's `sm`, `md`, or `lg` variants to switch the application's
mobile/desktop behavior. The shipped source currently exposes no named custom
Tailwind mobile variant.

## Printing

Every React route already has a usable fallback: `app.css` loads with
`media="all"`, and its global `@media print` block hides the header, sidebar,
search, actions, overlays, and toasts; expands Cards; removes shadows; and
forces black content on white. A page that does not need a distinct paper
document should add no bespoke print architecture.

The global `@media print` block in `app.css` is intentionally outside every
named cascade layer. Normal unlayered author declarations outrank Tailwind's
normal layered utilities, so its plain declarations reliably replace screen
utilities such as `flex`, fixed widths, padding, and minimum widths. For
`!important` declarations, that layer precedence inverts: a layered declaration
outranks an unlayered one. Keep shared and bespoke raw print rules in that
unlayered block; never move it into `@layer components` (or any other named
layer). Element-local `print:` utilities remain appropriate for simple
visibility switches, but they do not replace the global unlayered print
contract.

When a route genuinely needs a bespoke layout, render a print section from the
same React data and business logic as the screen page. Keep it in the same page
tree, hidden on screen, and reveal it only for print.

```jsx
function ExamplePrintSection({ children }) {
  return (
    <section className="example-print-section" aria-label="Kinderliste">
      <h1>Kinderliste</h1>
      <ul>
        {children.map(child => <li key={child.id}>{child.full_name}</li>)}
      </ul>
    </section>
  );
}

function ExamplePage({ data }) {
  return (
    <>
      <main className="example-screen">{/* interactive screen UI */}</main>
      <ExamplePrintSection children={data.children} />
    </>
  );
}
```

Hide and reveal that section in the app stylesheet:

```css
.example-print-section {
  display: none;
}

@media print {
  .example-screen {
    display: none !important;
  }

  .example-print-section {
    display: block !important;
  }
}
```

Use utilities, including Tailwind print variants, for ordinary visual styling
where practical. Keep raw print CSS for mechanics that need it, such as
`@page`, named pages, and `break-before`/`break-after`/`break-inside`.

The action that prints is a normal shared Button and calls the browser API
directly:

```jsx
<Button
  className="mobile-icon-action"
  size="responsive-icon"
  type="button"
  aria-label="Drucken"
  onClick={() => window.print()}
>
  <span className="desktop-action-label">Drucken</span>
  <Printer className="mobile-action-label" aria-hidden="true" />
</Button>
```

If the print data must be loaded on demand, render it first and call
`window.print()` only after React has committed the print section. Keep loading
and error handling in the page instead of reviving stylesheet-media changes or
server-rendered print bodies.

A separate React route is allowed only when the printout is genuinely a
different document with its own data contract or workflow, as with the Happy
Cleaning number list. A different arrangement of data already present on the
screen is not enough: use a same-page hidden section, as the kitchen and
SWP-Einteilung pages do.

Never add:

- middleware HTML/body injection;
- a hidden server-rendered legacy root;
- a second legacy or Bootstrap print stylesheet;
- runtime changes to a stylesheet's `media` attribute; or
- duplicated business logic that can drift from the screen page.

Before shipping a bespoke layout, verify the screen route and print preview.
Preserved operational documents also require browser evidence at the same data
and viewport as their previous output.

## Verification

Behavior belongs in the existing rendered-DOM seams, not class-name snapshots:

- shared Button, Card, Table, DataTable, Header, and breakpoint behavior in
  `frontend/src/components.test.jsx`;
- page behavior in the owning domain test;
- cascade, overflow, responsive appearance, and print fidelity in browser QA.

Run the complete frontend suite and rebuild the checked-in bundle:

```bash
cd frontend
npm run test
npm run build
```
