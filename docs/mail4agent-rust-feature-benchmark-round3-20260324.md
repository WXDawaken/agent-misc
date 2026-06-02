# Mail4Agent Rust Feature-Port Round 3

## Goal

Follow the completed bridge analysis with a more discriminating control batch.

This round is not meant to answer whether `subagents` or `single_xhigh` wins globally.

It is meant to test the current task-shape hypothesis:

- `single_xhigh` remains strongest on bounded Rust feature-port work
- `subagents` becomes more competitive when the task has hidden contracts or enough side questions to diffuse a single serial solve path

## Selected Tasks

- `large_mail4agent_rust_export_import_environment_bundle`
- `large_mail4agent_rust_delivery_audit_timeline`
- `medium_mail4agent_rust_routing_explain_surface`

The rationale for this slate lives in:

- `E:\agent_misc\docs\mail4agent-rust-feature-followup-tests-20260324.md`

## Seed Strategy

Each task uses a feature-specific template workspace built from:

- a completed Python feature workspace as the semantic oracle
- the validated native Rust mailbox-server baseline overlaid from the current Rust feature seed line

Current seed paths:

- export/import:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_export_import_round1_20260324`
- delivery audit:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_delivery_audit_round1_20260324`
- routing explain:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_routing_explain_round1_20260324`

Shared benchmark settings:

- manifest: `E:\agent_misc\benchmarks\mail4agent_rust_feature_workspace_manifest.toml`
- isolated benchmark `CODEX_HOME`
- explicit parent-agent pinning to `gpt-5.4 + xhigh`

## Validation Model

Each task now has a Rust-facing objective validation:

- `test/test_rust_export_import_environment_bundle.py`
- `test/test_rust_delivery_audit_timeline.py`
- `test/test_rust_routing_explain_surface.py`

These validations seed SQLite with the Python helper, launch the Rust server, and then drive the current Python feature clients/tests against that Rust server.

## Current Launch Policy

Start with the first large control:

- `large_mail4agent_rust_export_import_environment_bundle`

If that paired run is clean, continue with the remaining large control and then the medium explanatory control.

## Status

- The new seeds are materialized.
- The new validations compile.
- `tasks.toml` now includes all three new Rust feature-port task ids.
- The first paired follow-up run is now complete:
  - task: `large_mail4agent_rust_export_import_environment_bundle`
  - results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_export_import\20260324T031103Z`
  - objective analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_export_import\20260324T031103Z\analysis.md`
- Objective readout for that first large control is cleanly one-sided:
  - `single_xhigh`: `535.385s`, `1,382,291` total tokens, `168,519` fresh input
  - `subagents`: `837.395s`, `3,698,213` total tokens, `262,553` fresh input
- Both modes passed validation, but the solve paths diverged:
  - `single_xhigh` stayed on a short serial path: add admin-token-gated `/admin/*`, forward bundle/topology ops through the SQLite helper, clean up pipe-handle warnings, then rerun validation.
  - `subagents` used helper agents, but one helper initially recommended a broader native-Rust implementation path before the parent converged back to the same bridge-forwarding shape; that extra coordination and exploration showed up as higher event count and token use.
- Current interpretation:
  - This first non-bridge large control supports the existing task-shape hypothesis rather than weakening it.
  - On bounded large Rust feature-port work with a relatively direct semantic oracle, `single_xhigh` still looks like the stronger default.
  - A blinded judged-quality pass is still missing for this pair.
- The next large control is now complete:
  - task: `large_mail4agent_rust_delivery_audit_timeline`
  - results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_delivery_audit\20260324T035239Z`
  - objective analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_delivery_audit\20260324T035239Z\analysis.md`
  - stable live dashboard: `http://127.0.0.1:8036`
- Objective readout for the delivery-audit control also leans `single_xhigh`:
  - `single_xhigh`: `426.431s`, `1,253,005` total tokens, `181,923` fresh input
  - `subagents`: `499.058s`, `2,059,392` total tokens, `180,615` fresh input
- Current interpretation after two non-bridge large controls:
  - `export_import_environment_bundle` is strongly pro-`single_xhigh`.
  - `delivery_audit_timeline` is still pro-`single_xhigh` on wall-clock and total tokens, but much closer on fresh input.
  - A blinded judged-quality pass for those two completed large controls now exists at `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_large_nonbridge_judge_packets\judged_analysis.md`.
  - That judged readout is split rather than one-sided: `delivery_audit_timeline` preferred `subagents`, while `export_import_environment_bundle` preferred `single_xhigh`.
  - Across the 2 judged pairs, `single_xhigh` still holds the slightly higher mean judged score (`4.750` vs `4.625`), but pair preference is tied `1 : 1`.
  - The next most informative step is now the medium explanatory control `medium_mail4agent_rust_routing_explain_surface`, unless we decide to spend another replicate on one of the large non-bridge controls first.
- The medium explanatory control is now complete:
  - task: `medium_mail4agent_rust_routing_explain_surface`
  - results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_routing_explain\20260324T043942Z`
  - stable live dashboard: `http://127.0.0.1:8037`
  - objective analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_routing_explain\20260324T043942Z\analysis.md`
  - blind judged analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round3_medium_judge_packets\judged_analysis.md`
- Objective readout for the medium explanatory control strongly favors `single_xhigh`:
  - `single_xhigh`: `475.184s`, `1,578,867` total tokens, `84,175` fresh input
  - `subagents`: `883.650s`, `2,765,084` total tokens, `203,103` fresh input
- Judged readout for the same pair is narrower and slightly different in shape:
  - mean judged score is tied at `4.750` vs `4.750`
  - pair preference still went to `subagents`
  - the deciding reason was artifact polish, not task correctness: both passed, but the preferred packet had already removed the Windows harness `ResourceWarning` noise
- Round-3 working interpretation:
  - On all three selected controls, objective results now lean toward `single_xhigh`.
  - The judged signal is more mixed:
    - `export_import_environment_bundle` preferred `single_xhigh`
    - `delivery_audit_timeline` preferred `subagents`
    - `routing_explain_surface` preferred `subagents` on pair preference despite tied rubric totals
  - This keeps the earlier bridge-pattern hypothesis intact but also suggests that judged preference can still drift toward `subagents` on tasks where both candidates are correct and the remaining differences are about artifact polish or hidden contract cleanup.
