# Use one atomic aggregate command for complete kid edits

- **Status:** Accepted
- **Date:** 2026-08-02
- **Implementation:** `budo_app/kid_edit_commands.py`
- **Contracts:** `budo_app/kid_edit_contracts/`
- **Write seams:** `budo_app/kid_edit_writes.py`
- **Original design:** [GitHub issue #156](https://github.com/dasomji/BuDoBase/issues/156)

## Context

Editing a child spans data with different persistence rules: ordinary `Kinder`
fields, Schwerpunkt links, the Happy Cleaning number, and one assignment per
Happy Cleaning event. The existing Happy Cleaning commands are complete
application commands. Each owns transaction, audit, idempotency, revision, and
publication behavior, so composing those commands would produce multiple
observable command completions and could leave the aggregate semantics unclear.

Concurrent writers also need narrower conflict detection than one global event
revision. An unrelated child's assignment must not make an otherwise current
child edit stale.

## Decision

A complete child edit is one application command implemented by
`execute_kid_edit()`. It accepts a fully decoded replacement command and owns one
outer `transaction.atomic()` boundary. The command validates and plans the
complete final state before applying domain writes.

The aggregate uses lock-assuming mutation seams rather than invoking the
standalone Happy Cleaning command wrappers. Standalone commands retain their own
public behavior, while the aggregate remains the sole owner of its audit row,
idempotency result, revision coalescing, and post-commit publication.

### Lock and scope protocol

The actor profile and active Turnus establish the authorization and isolation
boundary. Rows are then locked in a stable order: Turnus, Schwerpunkt periods
and focuses, Happy Cleaning stations, the child, the child's relationship rows,
and affected Happy Cleaning events. Collections are ordered by stable IDs.
This ordering must remain compatible with standalone writers to avoid lock
inversion and deadlocks.

Every submitted child, focus, event, station, and relationship is constrained to
the actor's active Turnus. Foreign and nonexistent identifiers are deliberately
indistinguishable to callers.

### Optimistic concurrency

Different projections retain different tokens:

- `Kinder.edit_version` covers editable scalar fields and Schwerpunkt links;
- `happy_cleaning_number_version` covers the child's Happy Cleaning number;
- assignment versions cover one child in one event;
- event revisions remain projection revisions for publication rather than a
  whole-form stale token.

A canonical change advances each owned token at most once. Legacy writers of a
covered projection must participate in the same child-lock/version protocol.

### Final-state validation

The command validates the complete intended state, not a sequence of partial
operations. In particular, a station assignment requires a non-null final Happy
Cleaning number. The command also validates exact configured period/event sets,
assignment targets, station capacity, number uniqueness, and all supplied
versions before writing.

### Idempotency, no-ops, and side effects

The command ledger binds actor, Turnus, request ID, action, and a keyed
fingerprint of the normalized command:

- an exact repeat returns the stored response with `replayed: true`;
- reuse with another action or payload returns a conflict;
- a canonical no-op records the minimal ledger result but changes no domain
  token, writes no `kid.edit` audit event, and publishes nothing;
- a successful mutation writes exactly one `kid.edit` audit event and one
  ledger result inside the transaction;
- invalidations are registered only after successful planning and run through
  `transaction.on_commit()`.

Any domain, audit, or ledger failure escapes the outer transaction and rolls
back the complete edit.

## Consequences

- Callers receive all-or-nothing behavior across the complete edit form.
- Lock order and version ownership are part of the application contract and
  require PostgreSQL concurrency tests when changed.
- New editable child projections must explicitly join the aggregate snapshot,
  validation, versioning, audit, and writer-inventory rules.
- The command is intentionally deeper than its HTTP controller; parsing and
  transport concerns remain in the contract/view modules.

## Rejected alternatives

- **Invoke standalone commands inside another transaction:** this duplicates
  command-owned audit, ledger, revision, and publication effects.
- **Save each form section independently:** this permits partial child edits.
- **Use one event revision for the whole form:** unrelated children would cause
  false conflicts.
- **Use unversioned many-to-many replacement:** concurrent writers could
  silently overwrite Schwerpunkt changes.
- **Rely only on availability checks:** database constraints remain necessary
  for number and assignment races.

## Verification references

The durable executable specification lives in:

- `budo_app/kid_edit_tests/test_aggregate_standalone_integration.py`
- `budo_app/kid_edit_tests/test_producer_endpoint.py`
- `budo_app/kid_edit_tests/test_producer_races.py`
- `budo_app/kid_edit_tests/test_writer_races.py`
- `budo_app/kid_edit_tests/test_uncovered_stale_saves.py`
