# Issue #118 print-cascade evidence

This directory records the targeted browser and pixel-difference evidence for
the print cascade restructure. The three `--print.pdf` and `--print.png` files
are the fixed outputs captured from the production frontend bundle against a
throwaway copy of the local design-system review SQLite database. The shared
review database and the frozen `before/` evidence were not changed.

Capture source: base commit `64fc2ee` plus the uncommitted issue #118 worktree
diff. Headless Chrome loaded the final rebuilt `budo_app/static/frontend`
bundle from the local Django development server.

`browser-report.json` records the live computed-style contracts for:

- the global bespoke print block having no cascade-layer ancestor;
- a Card that remains collapsed in React state expanding for print with both
  inline paddings restored;
- the Happy Cleaning to-do portal unmounting on `afterprint`, followed by a
  normal overview print; and
- the key computed geometry for Nummernliste, SWP-Einteilung, and Küche.

`pixel-diff-report.json` compares the fixed page-one PNGs and the previously
captured broken outputs with the frozen `design-system-refactor/before/` set.
Run `compare.py` after converting the captured PDFs at 100 dpi.

## Measured print deltas

All coordinates are pixels in the 828 × 1171 page-one PNGs rendered at 100
dpi.

| Output | Frozen before | Broken output | Fixed output |
|---|---:|---:|---:|
| HC paper panel horizontal bounds | x=55…772, 718px | x=70…757, 688px (15px inset per side) | x=55…772, 718px (0px edge/width delta) |
| SWP heading top | y=60 | y=119 (+59px) | y=63 (+3px) |
| Kitchen first menu table width | 328px | 718px (+390px) | 329px (+1px) |

The two residual PNG measurements are not layout-box drift:

- **SWP:** both PDFs have the same 595.92 × 842.88pt page and the same
  39.75,39.75…556.50,803.25pt paper/illustration rectangle. Live print-media
  geometry also places both `.allocation-print-page` and its heading at
  `top: 0`. The frozen heading uses a Type3 font while the fixed output uses
  Liberation Sans at the same 19.995pt size; their glyph origins and ink boxes
  differ. The +3px threshold edge therefore reflects the pre-existing font
  substitution, not a shifted heading box. A compensating offset would be a
  font-specific rule-by-rule hack and would move the correct layout box.
- **Küche:** the first header row occupies exactly 39.75…276.00pt in both
  PDFs: 236.25pt wide, a 0pt vector delta. At 100dpi that is 328.125px, so the
  observed 328/329px edge is raster pixel coverage. No CSS adjustment is
  warranted.

The exact PDF coordinates, fonts, glyph boxes, and classifications are emitted
under `pdf_geometry` in `pixel-diff-report.json`.

The whole-page mean absolute RGB deltas also moved in the expected direction:
HC 20.1337 → 17.6919, SWP 23.6824 → 23.4857, and Küche 9.0944 → 4.7466.
Whole-page color/typography differences that predate this ticket remain in
those broad values; the geometry metrics isolate the three cascade regressions
named by #118.

## Automated verification

- Focused Happy Cleaning test: 17 passed.
- Full frontend suite: 25 files, 256 tests passed.
- Production frontend build: passed.
- Built-bundle cascade audit: exactly one bespoke global print block, with a
  stylesheet-root parent, no `.react-actions` selector, and the Card padding
  plus transition reset present.
- `git diff --check`: passed.

## Commands

```bash
BASE_URL=http://127.0.0.1:8018 node docs/evidence/issue-118/capture.cjs

python3 -c "import fitz,glob; \
[fitz.open(p)[0].get_pixmap(dpi=100).save(p.replace('.pdf','.png')) \
for p in glob.glob('docs/evidence/issue-118/*--print.pdf')]"

python3 docs/evidence/issue-118/compare.py
```
