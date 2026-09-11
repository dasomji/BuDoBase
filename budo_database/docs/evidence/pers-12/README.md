# PERS-12 dependency updates — 2026-09-11

Ticket: https://plane.audiopoesis.com/personal/browse/PERS-12/

GitHub's live Dependabot API returned 71 open alerts (37 high, 33 medium,
1 low) across `requirements/base.txt` and `frontend/package-lock.json`.
The local updates address all 20 affected packages, grouped below. GitHub alert
closure must be verified after these manifests reach the default branch;
local audit success is not evidence that GitHub has closed the alerts.

| Package | Updated version | Open alert numbers at baseline |
| --- | --- | --- |
| @hono/node-server | 2.1.1 | #120 |
| @tiptap/core | 3.31.3 | #137, #131 |
| @vitest/mocker | 4.1.11 | #142 |
| brace-expansion | 5.0.9 | #110, #101 |
| browserslist | 4.28.9 | #136, #135 |
| djangorestframework | 3.18.1 | #127, #126 |
| fast-uri | 3.1.7 | #134, #133, #130, #129, #112, #98 |
| hono | 4.13.7 | #141, #140, #139, #115, #114, #113, #109 |
| idna | 3.19 | #84 |
| ip-address | 10.7.0 | #111, #103, #102 |
| js-yaml | 4.3.2 | #116 |
| nanoid | 3.3.19 | #121, #118 |
| pillow | 12.3.0 | #96, #95, #94, #93, #92, #91, #90, #89, #88, #87, #86, #85, #82, #81, #80, #78, #75 |
| postcss | 8.5.28 | #119, #99 |
| python-dotenv | 1.2.3 | #79 |
| qs | 6.16.0 | #138, #132 |
| requests | 2.34.2 | #77, #61 |
| sqlparse | 0.6.0 | #128, #125, #124, #123, #122, #76 |
| undici | 7.29.1 | #108, #107, #106, #105, #104 |
| urllib3 | 2.7.0 | #83, #74, #73, #72, #64, #62 |

The Python audit also found a Django advisory beyond the GitHub snapshot;
Django is updated from 5.2.16 to 5.2.17 within the existing LTS series.
During verification GitHub added alert #143 for Vitest itself, bringing the
default-branch total to 72. It shares the mocker advisory and is already fixed
by the selected Vitest 4.1.11 update.
Pillow's security fixes require the 12.x upgrade. Its
[12.0 migration notes](https://pillow.readthedocs.io/en/stable/releasenotes/12.0.0.html)
were checked against the application's image APIs, and existing upload,
resizing, EXIF, and first-aid photo tests are included in the backend suite.
REST Framework's [release notes](https://www.django-rest-framework.org/community/release-notes/)
and PyPI Python compatibility metadata were also reviewed.

## Other updates and deferred versions

Updated compatible releases of Base UI, Lucide, shadcn, Tailwind (4.3.3),
Testing Library, asgiref, boto3/botocore/s3transfer, Daphne, certifi,
charset-normalizer, django-phonenumber-field, pillow-heif, psycopg2, six,
typing_extensions, and timezone data. Tiptap packages are aligned at 3.31.3.
Replaced test tooling's `latest` ranges with explicit supported major ranges.
The frontend lockfile and Django-served compiled JS/CSS are regenerated.

Registry checks also found newer Django 6.1.1, pandas 3.0.5, NumPy 2.5.3,
dj-database-url 3.1.2, django-extensions 4.1, Gunicorn 26.2.0, packaging 26.3,
phonenumbers 9.0.39, Vitest 5.0.0, jsdom 30.0.1, and jest-dom 7.0.1.
These are deferred as separate migrations or compatibility work; current
production requirements retain Python 3.10 support. React 19.3.0, Vite 8.3.0,
and plugin-react 6.1.1 are also available but their deliberate exact pins are
retained for a focused renderer/build-tool update. No claim is made that those
deferred releases are incompatible.

## Validation

- `npm ci`: clean lockfile install.
- `npm audit --json`: zero vulnerabilities (baseline: 24 affected npm packages,
  including propagated dependency findings; this count differs from GitHub alerts).
- `pip-audit -r requirements/production.txt`: zero known vulnerabilities
  (baseline: 66 findings across 8 resolved packages).
- Compared every installed affected package version against GitHub's live
  vulnerable-version ranges: 37 npm alerts and 35 Python alerts checked,
  zero vulnerable matches (including newly added #143).
- `npm test`: 35 files, 414 tests passed on Node 22.22.2 / Vitest 4.1.11.
- `npm run build`: passed; existing large-bundle warning remains.
- Python 3.12.13, SQLite, `python -Wd manage.py test`: 802 tests, 57 skipped,
  no failures. Existing Django 6 deprecation warning remains.
- All six [GitHub CI checks](https://github.com/dasomji/BuDoBase/actions/runs/34551129010)
  passed for dependency commit `7092846`. Both Python 3.10 and 3.12.13 ran
  802 tests with 57 SQLite skips; PostgreSQL 16/Redis 7 ran 802 tests with
  only one skip. CI also verified committed generated assets and production
  static collection/S3 URL configuration.
- `uv pip check`, Django `check`, `makemigrations --check --dry-run`, and
  production `check --deploy` with dummy CI configuration: passed.
- Production requirements resolve for Python 3.10 as well as 3.12.
- Local Python 3.10.6/PostgreSQL 18, `manage.py test --keepdb --noinput`:
  802 tests passed with 2 skips. The first run without `--keepdb` failed during
  database teardown because worker connections were still open; the rerun
  uses the same retention setting as CI. No application change was needed.
- Lizardtail preview rebuilt, static files collected with `--clear`, and process
  refreshed. Browser reload of the HTTPS login page succeeded; compiled JS/CSS
  both returned HTTP 200 and the login panel collapsed/expanded successfully.
  Browser smoke coverage is unauthenticated; authenticated API and upload
  behavior is covered by the automated suites.

After merge, query `gh api --paginate repos/dasomji/BuDoBase/dependabot/alerts`
again and check the alert numbers above. Do not close PERS-12 based only on
the local scans.
