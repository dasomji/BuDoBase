# Issue #122 — SWP-Einteilung mobile sticky controls

Captured from the working tree based on `5890eb8`, against a disposable copy
of `.artifacts/design-system-review.sqlite3`. The Django server used
development settings and an explicit local SQLite `DATABASE_URL`; the shared
review database and the repository's remote database configuration were not
used.

## Evidence

- Route: `/swp-einteilung-w1`
- Viewport: `390 × 844`, device scale factor `1`
- Browser: Google Chrome `150.0.7871.186`
- Measured header bottom: `73.1875px`
- Published `--app-header-height`: `73.1875px`
- Sticky controls computed `top`: `73.1875px`
- Sticky controls top after page scroll: `73.1875px`
- Kids-table scroll position: `0px → 4224px`
- Result: the SWP overview and **Kinder filtern** input remain pinned directly
  below the measured header while the kids table is scrolled.
- Runtime issues: no failed HTTP responses, page errors, or console errors.

[390px after-scroll screenshot](swp-einteilung-w1--390-after-scroll.png)

The same capture checks the desktop rendering at `1280 × 900`: the controls
compute to `position: static` and `top: auto`, so the desktop flex/scroll
structure remains in charge.

## Reproduce

From the repository root, prepare ignored local QA dependencies and a
disposable database copy, then start the server:

```bash
mkdir -p .artifacts/baseline
cp /path/to/review/.artifacts/design-system-review.sqlite3 \
  .artifacts/issue-122-review.sqlite3
cp /path/to/review/.artifacts/baseline/username.txt \
  .artifacts/baseline/username.txt
ln -s /path/to/review/.artifacts/tools .artifacts/tools

DJANGO_SETTINGS_MODULE=budo_database.settings.development \
DATABASE_URL="sqlite:////absolute/path/to/.artifacts/issue-122-review.sqlite3" \
python3 manage.py runserver 127.0.0.1:8012 --noreload
```

In another shell:

```bash
BASE_URL=http://127.0.0.1:8012 \
node docs/evidence/issue-122/capture.cjs
```

The capture script logs the mobile before/after and desktop measurements. It
dismisses and removes only the transient login-success toast before taking the
layout screenshot so that the header remains visible in the artifact.
