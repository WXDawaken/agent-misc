# Mail4Agent Rust Feature-Port Round 4

## Goal

Probe one more bounded Rust feature-port task on the new language split:

- Python remains the product semantic source of truth
- Rust selectively ports backend capabilities with clear boundaries

This round focuses on a backend-and-CLI feature only:

- `medium_mail4agent_rust_admin_mailbox_access`

The admin page is intentionally out of scope for this task.

## Selected Task

- `medium_mail4agent_rust_admin_mailbox_access`

## Seed Strategy

Template workspace:

- `E:\agent_misc\.tmp_test\mail4agent_rust_admin_mailbox_access_round1_20260324`

This seed combines:

- the validated Python admin-mailbox-access implementation as the semantic oracle
- the native Rust mailbox-server feature baseline from the current Rust feature-port line

Shared benchmark settings:

- manifest: `E:\agent_misc\benchmarks\mail4agent_rust_feature_workspace_manifest.toml`
- isolated benchmark `CODEX_HOME`
- explicit parent-agent pinning to `gpt-5.4 + xhigh`

## Validation Model

Rust-facing objective validation lives in:

- `test/test_rust_admin_mailbox_access.py`

The validation seeds SQLite with the Python helper, launches the Rust server, and then drives the current Python admin-mailbox HTTP plus CLI flow against that Rust server.

## Scope Notes

This round is intentionally limited to:

- direct admin-token use of the current core mailbox routes
- backend route semantics
- CLI compatibility for `--admin-token` and `MAILBOX_ADMIN_TOKEN`

It intentionally excludes:

- admin page or setup page UI work
- a broader admin-console redesign

## Status

- The seed workspace is materialized.
- Rust-facing validation is now added as `test/test_rust_admin_mailbox_access.py`.
- `tasks.toml` now includes `medium_mail4agent_rust_admin_mailbox_access`.
- The first paired benchmark pass is now complete:
  - results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access\20260324T093640Z`
  - objective analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access\20260324T093640Z\analysis.md`
  - stable live dashboard: `http://127.0.0.1:8010/dashboard.html`
- Objective readout currently favors `subagents` on every measured runtime axis:
  - `single_xhigh`: `918.284s` adjusted, `4,667,757` total tokens, `341,860` fresh input
  - `subagents`: `801.430s` adjusted, `4,343,110` total tokens, `233,346` fresh input
- Both modes passed validation, but the changed-file footprint differed:
  - `single_xhigh` touched 6 files, including shared Rust feature harness wiring plus README notes
  - `subagents` touched 4 files and stayed on the narrower app/backend/test-support surface
- Current interpretation:
  - This task does not look like the earlier Python admin-mailbox split, where `r1` and `r2` traded wins.
  - On the Rust side, this first paired readout is cleaner and currently supports `subagents` as the stronger fit for this bounded admin-token backend port.
- A blinded judged-quality pass now also exists:
  - judge bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access_judge_packets`
  - deblinded report: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access_judge_packets\judged_analysis.md`
- Judged readout slightly differs from objective:
  - pair preference preferred `single_xhigh`
  - score delta was only `1` point (`19` vs `18`)
  - judge rationale favored the candidate with cleaner validation evidence and tighter support implementation, even though it touched slightly more support surface
- Updated interpretation:
  - Objective currently leans clearly `subagents`.
  - Judged currently leans narrowly `single_xhigh`.
  - This makes the Rust admin-mailbox task look more like a bounded control with a mild evidence-polish split than like the earlier Rust bridge pattern where judged repeatedly preferred `subagents`.
- A reversed-order `r2` replicate is now in flight:
  - results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access_r2\20260324T110153Z`
  - `alternate_mode_order = true`
  - current run: `medium_mail4agent_rust_admin_mailbox_access__subagents__r2`
  - stable live dashboard: `http://127.0.0.1:8010/dashboard.html`
- The purpose of `r2` is to test whether this first-pass `objective -> subagents / judged -> single_xhigh` split survives a counterbalanced replicate.
