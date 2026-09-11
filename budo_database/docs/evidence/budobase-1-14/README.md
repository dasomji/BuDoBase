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
