# Issue #90 browser QA

Issue #90 registers the BuDoBase brand colors as canonical Tailwind theme
tokens, aliases the shadcn and legacy custom properties to those tokens, and
restores the Happy Cleaning child-search result highlight through the semantic
secondary color.

## Automated verification

- `cd frontend && npm run test -- src/domains/happyCleaningAssignment.test.jsx src/components.test.jsx`:
  2 files, 35 tests passed.
- `cd frontend && npm run test`: 24 files, 239 tests passed.
- `cd frontend && npm run build`: passed.
- The production bundle contains primary `#ffdd9b`, primary hover `#e6c78b`,
  secondary `#a9cfef`, and secondary hover `#8fb8d9`.
- Source scanning confirms the dead `.dark` palette, custom variant, and
  remaining `dark:` utility branches are absent.
- `git diff --check`: passed.

## Browser verification

The app was built and served on `127.0.0.1:8010` using only
`.artifacts/design-system-review.sqlite3` with this explicit override:

```text
DJANGO_SETTINGS_MODULE=budo_database.settings.development
DATABASE_URL=sqlite:////home/dev/Development/BuDoBase/budo_database/.artifacts/design-system-review.sqlite3
```

Production-browser computed styles resolved as follows:

| Contract | Computed value |
|---|---|
| `bg-primary` | `rgb(255, 221, 155)` |
| `bg-secondary` | `rgb(169, 207, 239)` |
| selected Happy Cleaning child result | `rgb(169, 207, 239)` |
| `--primary` / `--button-color` | `#ffdd9b` |
| `--secondary` / `--light-blue` | `#a9cfef` |

The selected-result check used the production selector and built stylesheet.
The review account receives redacted blank child names, so the normal seeded
page cannot open a name-filtered result without synthetic data; no intercepted
or mutated data was used for the evidence.

The affected route was recaptured at both viewports:

- [`hc-assignment--desktop.png`](hc-assignment--desktop.png)
- [`hc-assignment--mobile.png`](hc-assignment--mobile.png)
- [`report.json`](report.json)

The same two route captures update the `after/` side of
[`../design-system-refactor/review.html`](../design-system-refactor/review.html).
The server was stopped after capture. No review-database data was changed.
