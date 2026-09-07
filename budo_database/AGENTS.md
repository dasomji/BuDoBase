## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `dasomji/BuDoBase`; external pull requests are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

The canonical labels are `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Frontend design system

Frontend and UI work follows `docs/design-system.md` and the accepted ADR under `docs/adr/2026-07-26-frontend-design-system.md`.

### Page URL convention

Register new page routes with a trailing slash. `APPEND_SLASH` provides the
redirect from slashless GET requests. For historically slashless routes—most
importantly POST targets—use `legacy_slashless_page()` in `budo_app/urls.py`
so both forms resolve directly without losing POST data.

### Local server and React changes

Development now uses Lizardtail's local PostgreSQL 18 main database, initially
copied from Neon. The Neon URL in `.env` is not the development target. Start with
`lizardtail up` from the repository root; run database commands through
`lizardtail exec -- .venv/bin/python budo_database/manage.py <command>` so the
managed local `DATABASE_URL` overrides `.env`. In a feature worktree, initialize
the isolated clone with `lizardtail db migrate` before schema changes. Use the
`finish-and-cleanup` skill after a PR to migrate main after merge and remove the
feature resources. Do not merge feature database rows into main.

Use `lizardtail refresh` after frontend changes to build, collect static files,
and restart the managed preview together. Django's autoreloader handles Python
changes. Do not launch a separate unmanaged development server using `.env`.

The browser preview serves the compiled React bundle through Django; it does
not read `frontend/src/` directly. After changing React or frontend CSS, run:

```bash
cd frontend && npm run build
cd .. && python manage.py collectstatic --clear --noinput
```

The build updates `budo_app/static/frontend/`, while `collectstatic` refreshes
the ignored `staticfiles/` tree used by the long-running preview. Use `--clear`
even when no asset was deleted so an existing preview cannot keep serving a
stale bundle.

Python code is likewise loaded into the running Django process. The persistent
interactive preview must use Django's normal autoreloader; do not pass
`--noreload`:

```bash
python manage.py runserver 127.0.0.1:<existing-port>
```

Reserve `--noreload` for short-lived, deterministic test/evidence servers that
will be stopped after a bounded check. If the exposed preview is running with
`--noreload`, restart that exact server without the flag before continuing;
rebuilding React or collecting static files does not reload Python. Do not
start a duplicate server on another port, and preserve the existing
environment—especially `DATABASE_URL`—and its Tailscale mapping.

Before reporting completion, verify the actual exposed page after a hard
refresh. For changes spanning frontend and backend, also inspect the live API
response or exercise the changed interaction in the browser; passing tests and
fresh source files alone do not prove that the preview process loaded them.
