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
