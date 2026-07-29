# Issue #95 browser print QA

Issue #95 makes the React application the print source for every route and
removes the legacy Django-body print path.

## Automated verification

- Django React-shell tests: 23 passed.
- Targeted frontend print/domain tests: 43 passed.
- Full frontend suite: 24 files, 239 tests passed.
- Production frontend build: passed.

The shell contract checks that the app stylesheet uses `media="all"` and that
the response has no legacy print root, route print flag, Bootstrap print CDN,
or duplicate legacy stylesheet. The Happy Cleaning test checks that station
to-dos are rendered before `window.print()` without changing stylesheet media.

## Browser verification

The production bundle was served at `127.0.0.1:8011` with only:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

The targeted design-system capture completed with HTTP 200 for dashboard, All
Kids, kitchen, Happy Cleaning number list, and SWP-Einteilung. The following
print evidence is in the maintained after set:

- [Dashboard React fallback](../design-system-refactor/after/dashboard--print.png)
- [All Kids React fallback](../design-system-refactor/after/all-kids--print.png)
- [Kitchen bespoke output](../design-system-refactor/after/kitchen--print.png)
- [Happy Cleaning number list](../design-system-refactor/after/hc-nummernliste--print.png)
- [SWP-Einteilung](../design-system-refactor/after/swp-einteilung-w1--print.png)

The fallback pages contain the current React DOM, have no header/sidebar/action
chrome, render closed cards expanded, and use black text on white paper.
Side-by-side inspection against the issue #89 state confirmed that the kitchen,
Happy Cleaning number-list, and SWP document structure, content, and pagination
remain unchanged.

The Happy Cleaning number-list comparison also verifies that the generic
black/white fallback does not replace its bespoke gray radial paper gradient.
After excluding that print root from the fallback reset, its mean pixel delta
against the committed issue #89 reference fell from 21.72 to 9.69; visual
inspection confirms the established layout and background are restored.

Happy Cleaning station to-dos were captured through the real overview print
button:

- [Seven-page station to-do PDF](happy-cleaning-station-todos--print.pdf)
- [Page-one station preview](happy-cleaning-station-todos--print.png)
- [Browser assertions](report.json)

The browser assertions record seven station documents, `media="all"` on the
React stylesheet, no legacy print root, and a hidden header in print media.
The review database was not mutated, and the server was stopped after capture.
