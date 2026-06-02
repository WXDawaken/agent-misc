# Mail4Agent Language Backlog

## Goal

Turn the current `Python-first, Rust-selective` decision into a concrete work queue.

This backlog is not a rewrite plan.

It is a capability split:

- what should keep landing in Python
- what should be benchmarked or hardened in Rust
- what should stay shared and contract-driven

## Python Track

These are the next capabilities that should still be treated as Python-primary.

### Product and Policy

- new mailbox feature semantics
- auth/session policy changes
- harness/session/admin permission shaping
- operator workflow design

### UX and Surface

- CLI defaults and operator ergonomics
- admin page mailbox access UI
- future operator dashboards
- documentation that defines expected product behavior

### Suggested Near-Term Tasks

- admin page support for mailbox access using the new admin-token backend path
- any future session or token introspection surfaces
- any changes that redefine routing or visibility policy

## Rust Track

These are the best current Rust-primary candidates.

### Bounded Backend Controls

- export/import environment bundle
- delivery audit timeline
- routing explain backend slices when the surface is already clear

### Integration and Bridge

- webhook or stdio bridge delivery
- bridge heartbeat/retry handling
- backend route parity for already-stabilized Python features

### Server Hardening

- native Rust server slices that reduce subprocess or bridge overhead
- backend cleanup that improves validation evidence without widening product scope

### Suggested Near-Term Tasks

- Rust port of `medium_mail4agent_admin_mailbox_access` backend and CLI semantics, but still no admin page work
- one more bounded backend capability that already has a stable Python acceptance test
- targeted bridge cleanup only when it improves a known judged-quality gap

## Shared Contract Track

These should stay explicitly shared between the two language tracks.

- HTTP route contracts
- machine-readable CLI output shapes
- mailbox lifecycle semantics
- acceptance tests
- benchmark and judged-quality memos

## Promotion Gates

Promote a capability from `Python primary` to `Rust primary` only when:

- the Rust implementation no longer depends on Python as the semantic oracle for that capability
- repeated objective runs are competitive or better
- judged quality is not consistently worse
- the Rust implementation stays narrow and does not require cleanup churn to remain acceptable
- operator-facing evidence remains clear

## Current Recommendation

Use the next cycle like this:

1. Keep new feature requests landing in Python first.
2. Pick only bounded backend follow-ups for Rust.
3. Do not move the admin page or broader operator UX into Rust.
4. Revisit the split only after at least one capability fully clears the promotion gates.
