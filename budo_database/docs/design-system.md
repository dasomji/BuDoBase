# BuDoBase frontend design system

This guide is the contract for new and migrated React UI. It documents the
shared APIs shipped in `frontend/src` and the decisions recorded in
[the design-system ADR](adr/2026-07-26-frontend-design-system.md).

The frontend is still being migrated away from legacy global CSS. Existing
legacy markup is not precedent for new work. Prefer Tailwind utilities and the
shared components described here.

## Source locations

- Tokens and shared component styling:
  [`frontend/src/app.css`](../frontend/src/app.css)
- Button:
  [`frontend/src/components/ui/button.jsx`](../frontend/src/components/ui/button.jsx)
- Card and DataTable:
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
| `secondary` | `#a9cfef` | Supporting actions |
| `secondary-hover` | `#8fb8d9` | Secondary action hover |
| `secondary-foreground` | `#373737` | Text/icons on secondary |
| `muted` | `rgb(183 220 255 / 34%)` | Muted blue surface |
| `muted-foreground` | `#5f6368` | Muted text |
| `accent` | `rgb(179 202 217 / 95%)` | Strong blue chrome/header surface |
| `accent-foreground` | `#373737` | Text on accent |
| `success` | `#4caf50` | Success and money-add actions |
| `success-foreground` | `#373737` | Text/icons on success |
| `destructive` | `#d9534f` | Destructive and money-remove actions |
| `destructive-foreground` | `#ffffff` | Text/icons on destructive |
| `border` | `#dddddd` | Borders |
| `input` | `#dddddd` | Input borders |
| `ring` | `#737373` | Focus rings |
| `surface` | `rgb(222 240 255 / 70%)` | General translucent blue surface |
| `surface-solid` | `#def0ff` | Opaque blue surface |
| `surface-subtle` | `rgb(183 220 255 / 34%)` | Subtle blue surface/row |
| `surface-header` | `rgb(179 202 217 / 95%)` | Blue header/table chrome |

The `:root` properties such as `--button-color`, `--light-blue`, `--blue`,
`--dark-blue`, and `--bg-blue` are compatibility aliases for code that has not
yet migrated. Do not introduce new uses of those aliases. Dark mode is not part
of the current system.

## Button

Import the shared Button directly:

```jsx
import { Button } from '../components/ui/button';
```

`Button` renders a real button by default. Supplying `href` renders an anchor
with the same visual contract. A disabled anchor receives `aria-disabled`,
leaves the tab order, and prevents activation.

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

Available sizes are `default`, `xs`, `sm`, `lg`, `icon`, `icon-xs`,
`icon-sm`, and `icon-lg`. `size="icon"` is the 32px circular icon action.
Every icon-only action needs an `aria-label`; decorative icons must be hidden
from assistive technology.

```jsx
<Button size="icon" aria-label="Drucken" onClick={() => window.print()}>
  <Printer aria-hidden="true" />
</Button>
```

Header actions that keep text on desktop and become a circular icon on mobile
use the shipped responsive label pattern:

```jsx
<Button
  className="mobile-icon-action"
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

Card props:

| Prop | Contract |
|---|---|
| `title` | Required visible title and basis of the toggle's accessible name |
| `children` | Expandable content |
| `id`, `className` | Optional DOM id and additional classes |
| `initiallyClosed` | Start closed on desktop too |
| `headerAction` | Contextual action that does not toggle the card |
| `showToggleIcon` | Explicitly override icon visibility |
| `as` | Container element/component; defaults to `section` |
| `headingLevel` | Heading level number; defaults to `2` |
| `expanded` | Controlled expanded state |
| `onExpandedChange` | Controlled-state callback |

Do not build a second collapse state around Card. Use `expanded` and
`onExpandedChange` when another component must control it.

## Tables: choose one of two tiers

Both tiers share the same blue header, striped rows, borders, and horizontal
scroll boundary. Every table should be inside `TableScroll`; scrolling is a
container behavior, never a page-wide minimum width.

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
            <input aria-label={`Notiz für ${child.full_name}`} />
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
`id`, `beforeFilter`, and the three `TableScroll` behavior flags. It never
generates a table id.

`showFilter` is not a general full-row search. It filters the first available
value from `row.filterText`, `row.full_name`, or `row.name`, using German
case-insensitive matching. Populate `filterText` when the visible name is
rendered from another shape. Do not expect values in arbitrary columns to
match.

`SearchTable` remains a compatibility alias for `DataTable`; new code should
use `DataTable`.

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

Some legacy rules still contain older thresholds while migration is in
progress. They are cleanup targets, not permitted alternatives for new work.

## Printing

Every React route already has a usable fallback: `app.css` loads with
`media="all"`, and its global `@media print` block hides the header, sidebar,
search, actions, overlays, and toasts; expands Cards; removes shadows; and
forces black content on white. A page that does not need a distinct paper
document should add no bespoke print architecture.

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
