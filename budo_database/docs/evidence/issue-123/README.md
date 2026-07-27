# Issue #123 browser evidence

Captured on 2026-07-27 from the rebuilt production frontend at 1280×900.
The Django development server used a disposable `/tmp` copy of
`.artifacts/design-system-review.sqlite3`; the shared review database was never
served or modified.

## Results

- Success: `#373737` on `#54b958` = **4.7942:1**.
- Destructive: `#ffffff` on `#b93f3b` = **5.4730:1**.
- Link: `#725500` = **6.9654:1** on the page and **6.2597:1** on the
  composited card token. The captured table link measures **6.0593:1** on its
  rendered row.
- Card-header focus: `#686868` against the rendered header = **3.3570:1**.
- Table-sort focus: `#686868` against the rendered table header =
  **3.3508:1**.

The values in `browser-contracts.json` were read from browser computed styles
and evaluated with the WCAG relative-luminance formula.

## Files

- `semantic-actions--desktop.png` — live success and destructive actions.
- `card-header-focus--desktop.png` — focused expandable card header.
- `table-sort-focus--desktop.png` — focused table sort button and readable
  amber station links.
- `browser-contracts.json` — computed colors, effective backgrounds, and
  ratios.
