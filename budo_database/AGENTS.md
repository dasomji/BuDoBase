## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `dasomji/BuDoBase`; external pull requests are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

The canonical labels are `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Frontend design system

Frontend and UI work follows `docs/design-system.md` and the accepted ADR under `docs/adr/2026-07-26-frontend-design-system.md`.

### Static collection after asset removal

After pulling a change that deletes static assets, run
`python manage.py collectstatic --clear --noinput`. The ignored local
`staticfiles/` tree is not pruned by a normal `collectstatic`, so stale files
can otherwise survive even though fresh production builds do not contain them.
