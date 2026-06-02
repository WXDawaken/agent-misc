# Mail4Agent Python Rust Split Plan

## Decision

Use a `Python-first, Rust-selective` split for `mail4agent`.

Do not treat Rust as the new full product home yet.

## Why

The current evidence does not support a full Rust takeover.

- The Python feature-extension line is still the most stable product-delivery path.
- Rust feature-port work is clearly viable, but its strongest results are task-shape dependent rather than universal.
- Rust bridge and integration tasks can be excellent candidates, but bounded feature work still frequently favors `single_xhigh` on the Python side or on the Rust-port side.
- Several Rust validations still treat the Python implementation as the semantic oracle, which means Rust is not yet an independent product source of truth.

## Split

### Keep In Python

These should remain the primary implementation surface for now:

- product semantics and new feature design
- auth and session policy
- admin and operator workflows
- CLI UX and operator ergonomics
- admin page and future UI work
- schema and storage policy changes that redefine product behavior
- the canonical acceptance tests that define mailbox behavior

Rationale:

- this is where the repo is currently most complete
- this is where new product decisions are easiest to express and validate
- this is still the cleanest place to keep the source of truth for behavior

### Push Toward Rust

These are the best near-term Rust targets:

- mailbox server vertical slices
- bridge and integration paths
- bounded server-side route additions with a clear Python oracle
- export/import and delivery-audit style operational controls
- performance-sensitive or deployment-sensitive backend paths

Rationale:

- the Rust line already shows that server-side feature-port work is possible
- bridge-like work benefits from narrower backend-focused implementations
- these paths can be validated against existing Python semantics without forcing a full rewrite

### Keep Shared Across Both

These should stay contract-driven rather than language-owned:

- HTTP route contracts
- CLI-visible JSON/result shapes
- mailbox lifecycle semantics
- benchmark acceptance tests
- judged-quality review packets and comparison memos

Rationale:

- this keeps Python as product truth without blocking selective Rust adoption
- it also makes future promotion from Python-backed to Rust-backed functionality measurable

## Practical Rule

When adding a new capability:

1. Define and stabilize the behavior in Python first.
2. Add or tighten the acceptance test in the Python line.
3. Only then decide whether the backend slice is a good Rust port candidate.
4. Port to Rust when the task is server-heavy, bounded, and has a clear oracle.

## Current Ownership Map

### Python-owned now

- mailbox product behavior
- admin-token behavior and policy
- operator-facing CLI behavior
- future admin page work
- the baseline docs that describe how the product is supposed to behave

### Rust-owned now

- experimental and benchmarked server implementations
- selective backend feature ports
- bridge-focused delivery experiments
- candidate future backend hardening work

### Not Ready For Rust Ownership Yet

- full admin/operator product surface
- UI-facing work
- full independent semantic ownership of mailbox behavior
- replacing Python as the primary spec for tests and docs

## Promotion Criteria

Move a capability from `Python primary` to `Rust primary` only when all of these are true:

- Rust no longer relies on Python as the semantic oracle for that capability
- repeated objective runs are at least competitive
- judged-quality is not consistently worse
- operator-facing evidence and validation stay clean
- the Rust implementation does not require broader scope or cleanup churn to stay correct

## Immediate Implication

For the next wave:

- keep new feature requests landing in Python first
- use Rust for selected backend follow-up ports
- do not start a full rewrite plan
- do not move the admin page or broader product UX into Rust yet

## Working Summary

`mail4agent` should continue as a Python-led product with Rust as a selective backend acceleration path.

That means:

- Python remains the product truth
- Rust remains the most promising place for bounded server-side and bridge-heavy slices
- migration should happen by capability, not by repo-wide rewrite
