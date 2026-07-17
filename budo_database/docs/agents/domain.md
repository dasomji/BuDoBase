# Domain docs

This is a single-context repository. Engineering skills should consume its domain documentation as follows.

## Before exploring

- Read `CONTEXT.md` at the repository root when it exists.
- Read ADRs under `docs/adr/` that touch the area being changed.
- If either location does not exist, proceed silently. Domain-modeling workflows create them lazily when terminology or decisions are resolved.

## Use the glossary vocabulary

When an output names a domain concept, use the term defined in `CONTEXT.md`. Do not drift to synonyms that the glossary explicitly avoids.

If a needed concept is absent, first reconsider whether the project already uses a different term. If the absence represents a real modeling gap, note it for a domain-modeling workflow.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, identify the conflict explicitly instead of silently overriding the earlier decision.
