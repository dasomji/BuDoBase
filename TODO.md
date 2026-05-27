# BuDoBase Refactor TODO

Goal: make the codebase safer, easier to change, and ready for summer camp operations.

## 1. Baseline Tooling And Checks

- [x] Create or reuse a `uv` virtual environment.
- [x] Install project runtime dependencies with `uv`.
- [x] Install project dev dependencies with `uv`.
- [x] Run `python manage.py check`.
- [x] Run the existing Django tests.
- [x] Record any baseline failures before refactoring further.

Baseline notes:

- Removed `pygraphviz==1.13` from dev requirements; `uv pip install -r budo_database/requirements/dev.txt` now passes.
- `python manage.py check` passes.
- Initial `python manage.py test` found 7 tests, with 5 failures and 1 error because `test_files/detail_test.xlsx` was missing. Tests now use mocked workbook data instead of a missing local fixture.

## 2. Security And Data Boundaries

- [x] Protect risky AJAX mutation endpoints with login and CSRF checks.
- [x] Scope high-risk kid mutations to the active `turnus`.
- [x] Process Excel uploads against the selected `Turnus`, not `Turnus.objects.last()`.
- [x] Review all remaining object lookups in views for missing active-turnus scoping.
- [x] Add tests for unauthenticated mutation rejection.
- [x] Add tests for cross-turnus mutation rejection.

## 3. View Layer Cleanup

- [x] Centralize active-turnus/profile access for new/refactored paths.
- [ ] Split `budo_app/views.py` by feature area.
  - [x] Move kids/travel/check-in/check-out views to `budo_app/kids_views.py`.
  - [x] Move Schwerpunkt/meal/SWP dashboard/einteilung views to `budo_app/schwerpunkte_views.py`.
  - [x] Move Auslagerorte views to `budo_app/auslagerorte_views.py`.
  - [x] Move Excel upload/export views to `budo_app/excel_views.py`.
- [x] Extract dashboard aggregation into a service/query function.
- [x] Remove redundant `request.user.is_authenticated` checks inside `@login_required` views.

## 4. Excel Import Refactor

- [x] Split Excel import into read, parse, create, and family-assignment steps.
- [x] Add tests for selected-turnus import behavior.
- [x] Add tests for import rollback on row/validation errors.
- [x] Replace broad parsing assumptions with explicit validation errors.

## 5. Model And Domain Logic

- [x] Move repeated Excel-ish empty-value cleanup into tested utility functions.
- [x] Fix `Kinder.get_alter()` when `turnus` is missing.
- [x] Fix `Kinder.is_birthday_during_turnus()` when birthday/turnus data is missing.
- [x] Fix `Kinder.get_clean_anmerkung_buchung()` to check `anmerkung_buchung`.
- [x] Move external Google Maps HTTP calls out of model `pre_save` signals.

## 6. Settings And Deployment Hygiene

- [x] Consolidate duplicate settings modules.
- [x] Remove insecure production-adjacent defaults.
- [x] Remove generated `staticfiles` output from Git tracking.
- [x] Ensure static/media settings are consistent for local and production.

## 7. Logging And Dead Code

- [x] Replace `print()` debugging with structured logging.
- [x] Delete stale commented-out view code near the top of `budo_app/views.py`.
- [x] Remove obvious unused imports from touched modules.
- [x] Remove unused or unreachable views/routes.

## 8. Frontend Cleanup

- [x] Deduplicate CSRF cookie helpers in static JavaScript.
- [x] Add a small shared CSRF helper.
- [ ] Check key workflows manually after backend changes.

## 9. Final Verification

- [x] Run `python manage.py check`.
- [x] Run all tests.
- [ ] Run a quick smoke test of login, dashboard, kid detail, check-in/out, travel toggles, pfand, and Excel upload.
- [x] Update this TODO with final status and known follow-up risks.

Final notes:

- Automated verification passes: `python manage.py check` and all 16 Django tests.
- Dev dependency installation now passes after removing `pygraphviz==1.13`; `graphviz==0.20.3` remains in dev requirements.
- Manual browser smoke testing was not completed in this pass.
- Splitting `budo_app/views.py` is partially complete: kids/travel, Schwerpunkt/meal, Auslagerorte, and Excel upload/export views now live in feature modules. Several supporting extractions are also done (`users/dashboard_services.py`, `budo_app/location_services.py`, `budo_app/text_cleaning.py`, and shared view utilities).
