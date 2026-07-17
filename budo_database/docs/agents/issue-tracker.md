# Issue tracker: GitHub

Issues and PRDs for this repository live as GitHub issues. Use the `gh` CLI for all operations and infer the repository from `git remote -v` when running inside the clone.

## Conventions

- **Create an issue:** `gh issue create --title "..." --body "..."`
- **Read an issue:** `gh issue view <number> --comments`
- **List issues:** `gh issue list --state open --json number,title,body,labels,comments`
- **Comment on an issue:** `gh issue comment <number> --body "..."`
- **Apply or remove labels:** `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- **Close an issue:** `gh issue close <number> --comment "..."`

## Pull requests as a triage surface

External pull requests are **not** a request or triage surface. Only GitHub Issues enter the engineering-skills triage workflow.

## Skill terminology

- When a skill says **publish to the issue tracker**, create a GitHub issue.
- When a skill says **fetch the relevant ticket**, run `gh issue view <number> --comments`.

## Wayfinding operations

The `$wb:wayfinder` map is one GitHub issue with child issues as investigation tickets.

- Label the map `wayfinder:map`.
- Label children with their `wayfinder:<type>` role.
- Prefer GitHub sub-issues and native issue dependencies when available.
- If those features are unavailable, use task lists and explicit `Part of #<map>` / `Blocked by: #<issue>` lines.
- Claim work with `gh issue edit <number> --add-assignee @me`.
- Resolve work by commenting with the result and closing the issue.
