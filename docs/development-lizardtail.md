# Managed development

The host main uses PostgreSQL 18 copied from the approved Neon development
database. The historical URL in `budo_database/.env` is not the managed development
target. `lizardtail exec -- .venv/bin/python budo_database/manage.py COMMAND`
provides the local database environment for Django tools. A new host needs a
verified development import before startup. PostgreSQL 18's pinned image uses
`database.volumePath: "/var/lib/postgresql"`; do not mount it like PostgreSQL 17.

## Preview updates

Create the root `.venv` with the project's dependencies and install the frontend
npm dependencies. Django runs with its normal autoreloader; do not add
`--noreload`. The preview serves compiled React assets, so after React/CSS changes
run `lizardtail refresh`. Its configured update builds `budo_database/frontend`
and runs `collectstatic --clear --noinput` before restarting the preview.
Readiness checks `/login/`, because `/` redirects unauthenticated visitors.
Verify both the changed page/API and the compiled frontend assets in the browser.

## Worktrees and daily use

The checked-in `lizardtail.project.json` declares services, readiness probes,
routes and database initialization. Install the project's normal dependencies
and provide its private environment file in each worktree. Do not commit secrets.
This workflow requires the managed Lizardtail CLI (0.2+), Linux user systemd,
Caddy and an already configured private Tailscale host. Run `lizardtail doctor`.
PostgreSQL and bucket containers additionally require rootless Docker.

Register `main` once in a dedicated checkout of the repository default branch:
`lizardtail plan --instance main`. The existing host main is already initialized;
do not re-import or reseed it. In each feature worktree, use the automatically
assigned identity rather than calling the feature `main`:

```sh
lizardtail plan
lizardtail db migrate
lizardtail up
lizardtail status
lizardtail logs
```

Database initialization clones the evolving local main data before applying
feature migrations. Worktrees have separate data, ports and stable named HTTPS
URLs. Open the application URL printed by `up` from a device on the tailnet.
Do not guess localhost ports or change allowed-host lists to wildcards. A plan
reserves an address; successful startup establishes readiness. Confirm the page
and its assets from the browser as well.

`lizardtail down` stops this instance and retains its data and reservations.
`lizardtail up` resumes it. Services survive the agent/terminal and logout;
a host reboot currently requires `up` again. Do not kill another worktree's
processes or reset shared Tailscale Serve configuration.

## Finish after merge

Use the `finish-and-cleanup` skill, which runs the independent `push-pr` workflow
first. After an actual merge, `lizardtail finish --pr NUMBER` from the clean
feature worktree verifies the exact PR head and the clean registered main checkout,
fast-forwards main, backs up its database, runs update actions and migrations,
and verifies startup before deleting the feature's resources. Keep the worktree
until this succeeds. A failed main migration preserves feature data. Main rows
are retained; feature rows are not copied back. Remove the clean feature worktree
only after checking main in the browser. Main and unrelated instances remain.
