# BUDOBASE-1 through BUDOBASE-14 dependency upgrades

This record documents the compatibility decisions and validation for the
focused dependency upgrades created after PERS-12. Version availability and
runtime metadata were rechecked against the official PyPI and npm registries
on 2026-09-11 before each change.

## BUDOBASE-7: packaging 26.3

- Upgraded `packaging` from 24.2 to 26.3.
- PyPI metadata requires Python 3.9 or newer, so this change preserves both the
  repository's Python 3.10 compatibility job and the Python 3.12 production
  runtime.
- The application does not import `packaging` directly. Compatibility is
  exercised through dependency installation, `pip check`, Django startup, and
  the backend suite.
- Validation: `python -m pip check`; all pinned base requirements parsed with
  `packaging.requirements.Requirement`; `DATABASE_URL='sqlite:///:memory:'
  python -Wd manage.py test` (802 passed, 57 skipped).

Upstream references:

- [packaging documentation](https://packaging.pypa.io/)
- [packaging on PyPI](https://pypi.org/project/packaging/)

## BUDOBASE-4: dj-database-url 3.1.2

- Upgraded `dj-database-url` from 2.3.0 to 3.1.2.
- The 3.0 release changed the extension registry API, but BuDoBase only calls
  the stable public `config()` function. The 3.1 line adds Django 6 support and
  requires Python 3.10 or newer, preserving the pre-Django-upgrade runtime
  policy.
- SQLite in-memory parsing, PostgreSQL credentials/options, SSL-required
  parsing, persistent-connection settings, development startup, and production
  deployment checks were exercised locally.
- Validation: `pip check` and Django development/production checks passed;
  SQLite ran 802 tests with 57 expected skips; managed PostgreSQL 18 ran all
  802 tests successfully.

Upstream references:

- [dj-database-url changelog](https://github.com/jazzband/dj-database-url/blob/master/CHANGELOG.md)
- [dj-database-url on PyPI](https://pypi.org/project/dj-database-url/)

## BUDOBASE-5: django-extensions 4.1

- Upgraded `django-extensions` from 3.2.3 to 4.1.
- The 4.0 release removed `pipchecker`; BuDoBase neither configures nor invokes
  it. No other django-extensions command is referenced by project code or
  automation.
- Python 3.12 and Django 5 are supported upstream. Installed-app discovery,
  Django system checks, and the available management-command registry were
  verified without optional shell/Graphviz dependencies.
- Validation: `pip check` and `manage.py check` passed; `graph_models`,
  `shell_plus`, and `show_urls` remain registered; `show_urls` successfully
  loaded and rendered the project's 219 URL entries.

Upstream references:

- [django-extensions changelog](https://github.com/django-extensions/django-extensions/blob/main/CHANGELOG.md)
- [django-extensions on PyPI](https://pypi.org/project/django-extensions/)

## BUDOBASE-8: phonenumbers 9.0.39

- Upgraded `phonenumbers` from 8.13.49 to 9.0.39.
- Upstream's Python history states that 9.0 is a major version only because the
  source Java library changed its required Java version; the Python package has
  metadata-only changes at that boundary. Later 9.0.x releases refresh number
  metadata.
- Representative German, Austrian, and international parsing, validation,
  E.164 normalization, national/international formatting, and
  `django-phonenumber-field` model/form integration were exercised.
- Validation: `pip check` passed; representative phone contracts passed; the
  focused profile and Leitung team-management suites passed all 21 tests.

Upstream references:

- [python-phonenumbers version history](https://github.com/daviddrysdale/python-phonenumbers/blob/dev/python/HISTORY.md)
- [phonenumbers on PyPI](https://pypi.org/project/phonenumbers/)

## BUDOBASE-6: Gunicorn 26.2.0

- Upgraded Gunicorn from 23.0.0 to the latest PyPI release, 26.2.0. Git tags
  and the development changelog contain later 26.2.x entries, but those builds
  are not published on PyPI and therefore are not installable release targets.
- Gunicorn now requires Python 3.10 or newer. BuDoBase's Railway `Procfile` and
  `railway.json` use Daphne/ASGI, so Gunicorn is a WSGI fallback rather than the
  configured production entrypoint; no worker configuration required migration.
- The 26.x HTTP parser tightened request handling and introduced optional HTTP/2
  and ASGI workers. BuDoBase retains the default sync WSGI worker and enables no
  new protocol options.
- Validation: `pip check`, Django system checks, and production migrations/static
  collection passed. A disposable production-configured Gunicorn process booted
  one sync worker, served `/login/` with HTTP 200 behind the configured proxy
  header, and shut its worker and master down cleanly on `SIGTERM`.

Upstream references:

- [Gunicorn 2026 changelog](https://github.com/benoitc/gunicorn/blob/master/docs/content/2026-news.md)
- [Gunicorn on PyPI](https://pypi.org/project/gunicorn/)

## BUDOBASE-3: NumPy 2.5.3 and Python 3.12 baseline

- Upgraded NumPy from 2.1.3 to 2.5.3, the latest PyPI release.
- NumPy 2.5 supports Python 3.12-3.14 and publishes CPython 3.12 manylinux
  wheels for both x86-64 and ARM64. It drops Python 3.11 and expires several
  NumPy 2.0 deprecations. BuDoBase does not import NumPy directly; it consumes
  arrays only through pandas' Excel paths and does not use the removed APIs.
- The repository's production runtime was already pinned to Python 3.12.13.
  Python 3.10 was retained only as a compatibility CI lane after PERS-12. The
  supported minimum is now explicitly Python 3.12 in README and CI so adopting
  NumPy 2.5 does not silently change runtime support.
- NumPy's 2.0 dtype promotion and copy-semantics changes predate the old 2.1.3
  pin. The focused import/export round trips remain the behavioral guard for
  pandas-backed data conversion.
- Validation: the CPython 3.12 manylinux wheel installed successfully;
  `pip check` passed; the Excel value parsing, upload authorization, import
  transaction, family/date handling, and export suites passed all 30 tests with
  pandas 2.2.3.

Upstream references:

- [NumPy 2.5 release notes](https://numpy.org/doc/2.5/release/2.5.0-notes.html)
- [NumPy 2.0 migration guide](https://numpy.org/doc/2.5/numpy_2_0_migration_guide.html)
- [NumPy on PyPI](https://pypi.org/project/numpy/)

## BUDOBASE-2: pandas 3.0.5

- Upgraded pandas from 2.2.3 to 3.0.5, the latest PyPI release, together with
  the already-validated NumPy 2.5.3 runtime.
- pandas 3 enables copy-on-write semantics, infers its dedicated string dtype
  by default, changes inferred datetime resolution, and removes APIs deprecated
  in earlier releases. BuDoBase does not assert exact pandas dtypes or mutate
  through chained assignment. Its reads use column/row selection and values are
  normalized to Python/Django types before persistence.
- pandas requires Python 3.11 or newer. The explicit Python 3.12 minimum adopted
  for BUDOBASE-3 satisfies that requirement.
- Excel ingestion, birthday/postal-code parsing, family assignment,
  transactional rollback, upload authorization, and Excel export round trips
  form the relevant compatibility seam.
- Initial validation exposed the intentional pandas 3 string-dtype rule in a
  test fixture: an all-string birthday column no longer accepts a numeric Excel
  ordinal. The fixture now declares object dtype, accurately representing the
  supported mixed-cell workbook input without weakening the assertion or
  changing production behavior.
- Validation: `pip check` passed; the final NumPy 2.5.3/pandas 3.0.5 combination
  passed all 30 focused Excel/import/export/family/date/upload tests with
  deprecation warnings enabled.

Upstream references:

- [pandas 3.0 release notes](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
- [pandas on PyPI](https://pypi.org/project/pandas/)

## BUDOBASE-1: Django 6.1.1

- Upgraded Django from the 5.2.17 LTS line to 6.1.1, the latest PyPI release.
- Django 6 requires Python 3.12 or newer. BUDOBASE-3 already made Python 3.12
  the explicit repository minimum, matching the existing production runtime.
- Removed `FORMS_URLFIELD_ASSUME_HTTPS`: Django 6 removed this transitional
  setting and HTTPS is now the built-in `URLField` default.
- Reviewed the 6.0 removals against the project: constraints already use
  `condition=`, model saves use keyword arguments, `DEFAULT_AUTO_FIELD` is
  explicit, and the project does not use removed renderer, prefetch, GIS, or
  formatting APIs. Django 6.1 supports PostgreSQL 15+ and SQLite 3.37+; CI uses
  PostgreSQL 16, local integration uses PostgreSQL 18, and the Python 3.12
  runtime supplies a supported SQLite.
- Django 6.1 introduces the `MAILERS` replacement. The project now explicitly
  configures the SMTP default that older Django versions supplied implicitly,
  preserving behavior while eliminating the Django 7 deprecation path. The
  synchronous join-request notification flow is unchanged.
- The complete production manifest was installed for compatibility testing;
  current Django REST Framework 3.18.1 loads successfully with Django 6.1.1.
- Validation: `pip check`, Django system/deployment checks, and
  `makemigrations --check --dry-run` passed; SQLite ran all 802 tests with 57
  expected skips; the post-`MAILERS` notification suite passed 17 tests with 2
  expected skips; managed PostgreSQL 18 ran all 802 tests successfully;
  `pip-audit` reported no known vulnerabilities.

Upstream references:

- [Django 6.0 release notes](https://docs.djangoproject.com/en/6.1/releases/6.0/)
- [Django 6.1 release notes](https://docs.djangoproject.com/en/6.1/releases/6.1/)
- [Django 6.1.1 release notes](https://docs.djangoproject.com/en/6.1/releases/6.1.1/)

## BUDOBASE-11: @testing-library/jest-dom 7.0.1

- Upgraded `@testing-library/jest-dom` from 6.9.1 to 7.0.1.
- The 7.0 boundary makes `@testing-library/dom` a required peer and raises the
  Node minimum to 22. BuDoBase resolves `@testing-library/dom` 10.4.1 through
  Testing Library React/user-event, satisfying jest-dom's `>=10 <11` peer; the
  repository runs Node 22.22.2 and CI tracks Node 22.
- The existing Vitest-specific setup import remains supported; no matcher
  assertions were changed.
- Validation: clean install/update, peer tree check, 35 test files and 414 tests
  passed, and `npm audit` reported zero vulnerabilities.

Upstream references:

- [jest-dom 7.0.0 release](https://github.com/testing-library/jest-dom/releases/tag/v7.0.0)
- [jest-dom 7.0.1 release](https://github.com/testing-library/jest-dom/releases/tag/v7.0.1)

## BUDOBASE-10: jsdom 30.0.1

- Upgraded jsdom from 29.1.1 to 30.0.1.
- jsdom 30 drops Node 20 and requires Node 22.22.2, 24.15, or 26+. CI now
  pins Node 22.22.2 explicitly and README records that frontend minimum.
- The release adds native `CSS.escape()`/`CSS.supports()`, pixel-normalized
  computed styles, and dependency updates. It exposed an integration defect in
  `css.escape`, used by jest-dom: that package exports an existing native
  operation as a bare function, while jsdom's Web IDL wrapper correctly checks
  its receiver. Test setup now binds jsdom's native `CSS.escape` before loading
  the jest-dom matchers. The existing `toHaveFormValues` assertion remains
  unchanged and passing.
- Validation: all 35 frontend test files and 414 tests passed, covering focus,
  navigation, forms, and editor interactions; `npm audit` reported zero
  vulnerabilities.

Upstream references:

- [jsdom 29.1.1 to 30.0.1 comparison](https://github.com/jsdom/jsdom/compare/v29.1.1...v30.0.1)
- [jsdom on npm](https://www.npmjs.com/package/jsdom)

## BUDOBASE-9: Vitest 5.0.0

- Upgraded Vitest from 4.1.11 to 5.0.0.
- Vitest 5 requires Node 22.12+ and Vite 6.4+. BuDoBase uses Node 22.22.2 and
  Vite 8.1.4, so both prerequisites are satisfied.
- Reviewed the Vitest 5 migration surface. The repository has no inline test
  projects, benchmark suites, browser-mode tests, custom reporters, removed
  entry-point imports, sequential test options, or worker-id assumptions.
- Vitest 5 enables `clearMocks` by default. The suite already establishes mock
  state within each test or hook, and the unchanged assertions pass with the
  new isolation behavior; no compatibility override was added.
- Validation: the resolved dependency tree contains Vitest 5.0.0, Vite 8.1.4,
  and jsdom 30.0.1; all 35 test files and 414 tests passed; `npm audit`
  reported zero vulnerabilities.

Upstream references:

- [Vitest 5 migration guide](https://vitest.dev/guide/migration/)
- [Vitest 5 announcement](https://vitest.dev/blog/vitest-5)
- [Vitest 5.0.0 release](https://github.com/vitest-dev/vitest/releases/tag/v5.0.0)
