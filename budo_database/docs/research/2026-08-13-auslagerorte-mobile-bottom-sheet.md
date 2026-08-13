# Auslagerorte mobile map bottom sheet

Date checked: 2026-08-13

## Executive recommendation

Replace the mobile map's hand-built pull-up list with the current **Base UI-backed shadcn Drawer**, configured as a controlled, non-modal bottom drawer with snap points. Keep the map interactive, give the list one explicit inner scroll container, and prevent that list from chaining scroll to the document.

This component change is worthwhile because Drawer owns the gesture and snap-point state that the current page reimplements. It is not, by itself, the viewport fix. The page must also stop mixing `svh` and `vh` in the same height chain. Use a dynamic viewport-sized map shell (`dvh`) and verify the actual mobile browsers because dynamic units deliberately resize while browser chrome retracts.

Do not use the existing shadcn Sheet for this interaction. Sheet is a suitable edge-positioned Dialog, but Drawer is the primitive that adds swipe gestures and snap points. Do not add the older Vaul-backed Drawer: current shadcn Base UI projects use Base UI Drawer, while Vaul's own repository says it is unmaintained.

## Current repository implementation

The Auslagerorte mobile list is **self-built**, not a shadcn component:

- `frontend/src/domains/places.jsx:300-328` defines `MobileListSheet` as an absolutely positioned `<div>` with local `open` state.
- Its two positions are custom height classes: `h-[5.5rem]` and `h-[55%]`.
- Its drag behavior is a custom `touchstart`/`touchend` calculation with a fixed 24 px threshold. It has no pointer gesture handling, velocity, intermediate snap points, drag cancellation, or library-managed arbitration between dragging and scrolling.
- `PlaceList` is an ordinary `<ul>` with `overflow-y-auto` (`frontend/src/domains/places.jsx:76-104`). That is appropriate semantic list markup, but the scroll boundary does not declare `overscroll-behavior`, so the browser may chain an exhausted list scroll to an ancestor/document.

The repository does contain a shadcn-style Sheet at `frontend/src/components/ui/sheet.jsx`, built on `@base-ui/react/dialog`, and uses it for the mobile application sidebar. The Auslagerorte list does not import or render it. The repository's `frontend/components.json` selects shadcn's `base-nova` style, and `frontend/package.json` already depends on `@base-ui/react` 1.6.0; adopting the current Base UI Drawer follows the accepted design-system direction without introducing another primitive family.

## Diagnosis of the reported browser behavior

The strongest code-level explanation is the mixed viewport sizing:

- The map shell is fixed at `calc(100svh - var(--app-header-height))` in `frontend/src/domains/places.jsx:405`.
- `.app-shell-content` also has `min-height: 100svh` in `frontend/src/app.css:765-770`.
- In the same document, `#root` has `min-height: 100vh` in `frontend/src/app.css:257-270`.

On current browsers, `vh` is equivalent to the **large** viewport height, whereas `svh` is the fixed **small** viewport height. The small viewport is the space available with browser interfaces expanded; it does not grow when the address/navigation bars retract. `dvh` follows the currently visible viewport as those interfaces expand or retract. [MDN: viewport-percentage length units](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/length#relative_length_units_based_on_viewport)

That makes the symptom internally consistent: the document/root can be as tall as the browser-chrome-hidden viewport (`100vh`/`100lvh`), while the app shell and map stay at the smaller chrome-visible height (`100svh`). Once a small page scroll hides the Brave or Firefox UI, the visible viewport becomes taller but the map and its percentage-height sheet do not. The remaining large-root area is exposed below as apparent blank space. The same excess document scroll range explains why it is possible to continue scrolling after the actual map UI ends.

This is a diagnosis from the inspected layout and platform sizing rules, not a direct physical-device reproduction. It should be confirmed on the affected Brave and Firefox versions by recording `document.documentElement.scrollHeight`, `clientHeight`, `window.innerHeight`, `window.visualViewport?.height`, the map-shell bounding rectangle, and the list scroll position before and after browser chrome retracts. If Google Maps needs an explicit geometry refresh after that transition, the platform exposes the visible viewport through `window.visualViewport` and its `resize` event. [MDN: Visual Viewport API](https://developer.mozilla.org/en-US/docs/Web/API/Visual_Viewport_API), [MDN: `VisualViewport.resize`](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport/resize_event)

The second issue is scroll ownership. At a nested scroller's boundary, continued scrolling can propagate to an ancestor, which MDN calls scroll chaining. Applying `overscroll-behavior-y: contain` to the actual list scroller prevents the underlying document from taking over; `none` additionally suppresses native boundary effects and is usually more aggressive than needed here. The property only works on an actual scroll container. [MDN: `overscroll-behavior`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overscroll-behavior)

## Component comparison

| Option | Fit for the map list | Findings |
|---|---|---|
| Current custom `MobileListSheet` | Weak | It provides a collapsed/expanded visual and a basic swipe threshold, but all gesture, snap, and scroll-boundary behavior is application code. |
| Existing shadcn Sheet | Partial | It gives accessible Dialog behavior and edge positioning. It does not document draggable snap points; Base UI explicitly says a Drawer is Dialog plus gestures and snap points. [Base UI Drawer usage guidance](https://base-ui.com/react/components/drawer#usage-guidelines) |
| Current shadcn Drawer (Base UI) | Best | It supports vertical snap points, controlled snap state, swiping, non-modal operation, pointer-dismissal control, and explicit swipe-ignore regions. It is designed for a bottom sheet. [shadcn Drawer](https://ui.shadcn.com/docs/components/base/drawer), [Base UI Drawer](https://base-ui.com/react/components/drawer) |
| Older shadcn Drawer (Vaul) | Do not introduce | Vaul offers the right conceptual API, but its official repository states that the project is unmaintained. Current shadcn Base UI Drawer has replaced it for this repo's selected component flavor. [Vaul repository](https://github.com/emilkowalski/vaul), [shadcn migration guidance](https://ui.shadcn.com/docs/components/base/drawer#migrating-from-vaul) |

Base UI Drawer became stable in v1.3.0, whose release notes include touch-selection and cross-axis-scrolling fixes. Version 1.6.0, already installed here, added a virtual-keyboard provider and more swipe-performance improvements, showing that the primitive is actively maintained. [Base UI v1.3.0 release](https://base-ui.com/react/overview/releases/v1-3-0), [Base UI releases](https://base-ui.com/react/overview/releases)

## Proposed interaction shape

Use shadcn Drawer with the following design constraints:

1. Keep it mounted/open over the mobile map and use `modal={false}` so users can still pan or select the map. Pair that with `disablePointerDismissal` so tapping the map does not close the list. Base UI documents both non-modal behavior and controlled `open` state. [Base UI Drawer non-modal example](https://base-ui.com/react/components/drawer#non-modal)
2. Use controlled snap points for the existing compact peek and an expanded list. A fixed `rem`/pixel peek plus a fractional full point is supported; fractions are relative to viewport height. `snapToSequentialPoints` can make multi-point movement distance-based rather than velocity-skipping. [Base UI Drawer snap points](https://base-ui.com/react/components/drawer#snap-points)
3. Keep the handle/header outside a single `flex-1 overflow-y-auto overscroll-y-contain` list region. shadcn specifically recommends a flex-item scroll region and warns against `h-full` inside its content-sized vertical Drawer. Its default vertical cap is `calc(100dvh - 6rem)`. [shadcn Drawer sizing and scrolling](https://ui.shadcn.com/docs/components/base/drawer#custom-sizes)
4. Use `data-base-ui-swipe-ignore` only for descendants whose touch gesture must never drag the drawer. Base UI exposes this escape hatch for gesture conflicts. [Base UI Drawer anatomy](https://base-ui.com/react/components/drawer#anatomy)
5. Preserve the existing `<ul>`/`<li>` list semantics and button selection behavior. Drawer replaces the containing interaction surface, not the domain list itself.
6. Use `100dvh` (minus the measured app header) for the overall map shell, remove or override conflicting large-viewport minimum heights for this full-screen route, and ensure the document itself has no residual vertical scroll range. MDN cautions that `dvh` can resize during scrolling, so animate the drawer transform/snap transition rather than globally animating height. [MDN: dynamic viewport units](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/length#dynamic_viewport_units)

The Drawer documentation also covers software-keyboard-aware behavior, but the list itself contains no form fields; that provider is not needed unless search/filter inputs move inside the drawer later. [Base UI Drawer virtual-keyboard guidance](https://base-ui.com/react/components/drawer#virtual-keyboard-aware)

## Verification criteria

Verify on physical or remotely debugged Android devices in both Brave and Firefox, with browser chrome initially visible and after it retracts:

- The document's `scrollHeight` does not exceed its intended visible application height; scrolling the list never reveals blank document space.
- The map shell's bottom edge follows the visible viewport bottom after chrome show/hide.
- The collapsed peek and expanded snap remain attached to the visible bottom edge.
- The expanded list scrolls independently; reaching its top or bottom does not scroll the document.
- Dragging the handle changes snap point, while vertical list scrolling does not accidentally drag the drawer.
- The map remains pannable/tappable outside the non-modal drawer.
- Tap, touch drag, pointer cancellation, keyboard focus, reduced motion, orientation changes, and the software keyboard while using the top search field remain usable.

Automated component tests should cover controlled snap state, list selection, accessible title/label, and collapsed/expanded state. The browser-chrome transition and real touch gesture arbitration require real-browser QA; a desktop responsive emulator does not reproduce retracting mobile browser UI reliably.
