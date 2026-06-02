# Mail4Agent Feature Benchmark Round 2

## Goal

Continue the Python product-extension benchmark line for `mail4agent` with three new tasks that lean into auth lifecycle, worker throughput, and environment reproducibility:

- session logout plus expiry introspection
- bounded batch claim for workers
- export or import of non-secret mailbox topology

## Selected Tasks

- `small_mail4agent_session_logout_and_expiry_introspection`
- `medium_mail4agent_batch_claim_and_ack`
- `large_mail4agent_export_import_environment_bundle`

## Shared Seed

- Template workspace: `E:\agent_misc\.tmp_test\mail4agent_feature_round2_20260322`
- Workspace manifest: `E:\agent_misc\benchmarks\mail4agent_feature_workspace_manifest.toml`

This round reuses the same Python-only product baseline as round 1, but adds benchmark-only validation for:

- auth-session invalidation and expiry metadata
- deterministic batch claim behavior plus worker-batch CLI support
- admin export or import of non-secret topology bundles

## Run Policy

These three tasks should run as matched comparisons:

- `single_xhigh`
- `subagents`

The point of this round is to keep the benchmark on Python product-extension work rather than language migration.

## Config Caveat

The first round-2 result sets were collected before the harness explicitly recorded `resolved_model` / `resolved_reasoning_effort` and before it passed reasoning effort to Codex CLI for every mode.

Treat these older result directories as provisional rather than fully apples-to-apples:

- `E:\agent_misc\benchmarks\results\20260322T141900Z_mail4agent_feature_round2\20260322T141646Z`
- `E:\agent_misc\benchmarks\results\20260322T155200Z_mail4agent_small_alt_order\20260322T154655Z`
- `E:\agent_misc\benchmarks\results\20260323T000000Z_mail4agent_medium_alt_order\20260322T161332Z`
- `E:\agent_misc\benchmarks\results\20260323T001500Z_mail4agent_large_alt_order\20260322T164819Z`

Those batches may have inherited a transient global reasoning-effort setting and therefore may contain configuration-driven regression or comparability noise.

Current explicit-config sanity reruns that pin `gpt-5.4` plus `xhigh` for both modes:

- Small: `E:\agent_misc\benchmarks\results\20260323T_simple_config_sanity\20260322T174804Z`
- Large: `E:\agent_misc\benchmarks\results\20260323T_large_config_sanity\20260322T182520Z`

The medium task has not yet been rerun under this explicit-config harness, so its older counterbalanced result is still provisional.

## Validation Entry Points

- `python -m unittest test.test_session_logout_and_expiry_introspection -v`
- `python -m unittest test.test_batch_claim_and_ack -v`
- `python -m unittest test.test_export_import_environment_bundle -v`

## Current Batch

- Results: `E:\agent_misc\benchmarks\results\20260322T141900Z_mail4agent_feature_round2\20260322T141646Z`
- Dashboard: `http://127.0.0.1:8023`
- Total runs: `6`
- Current status: objective batch completed

## Order-Bias Follow-Up

- Harness flag: `--alternate-mode-order`
- Behavior: keep the requested mode order on odd replicates and reverse it on even replicates
- Small-only counterbalance run: `E:\agent_misc\benchmarks\results\20260322T155200Z_mail4agent_small_alt_order\20260322T154655Z`
- That follow-up used `replicate_start=2` so the `small_mail4agent_session_logout_and_expiry_introspection` pair ran as `subagents -> single_xhigh`
- Medium-only counterbalance run: `E:\agent_misc\benchmarks\results\20260323T000000Z_mail4agent_medium_alt_order\20260322T161332Z`
- The medium follow-up also uses `replicate_start=2`, so `medium_mail4agent_batch_claim_and_ack` runs as `subagents -> single_xhigh`
- Live dashboard for the medium follow-up: `http://127.0.0.1:8024`
- Medium follow-up status: completed
- Medium counterbalance readout: `subagents` still won on wall-clock (`459.121s` vs `819.087s`), total tokens (`2,580,972` vs `3,422,189`), and fresh input (`159,787` vs `173,428`), so fixed mode order does not explain the original medium winner by itself
  This readout predates explicit model/effort pinning and should remain provisional until rerun.
- Large-only counterbalance run: `E:\agent_misc\benchmarks\results\20260323T001500Z_mail4agent_large_alt_order\20260322T164819Z`
- The large follow-up also uses `replicate_start=2`, so `large_mail4agent_export_import_environment_bundle` runs as `subagents -> single_xhigh`
- Live dashboard for the large follow-up: `http://127.0.0.1:8025`
- Large follow-up status: completed
- Large counterbalance readout: `subagents` still won on wall-clock (`653.342s` vs `785.300s`), while `single_xhigh` used fewer total tokens (`2,999,870` vs `3,669,028`) and fewer fresh input tokens (`91,176` vs `175,303`); fixed mode order again does not fully explain the original winner
  This readout is now superseded by the explicit-config rerun in `E:\agent_misc\benchmarks\results\20260323T_large_config_sanity\20260322T182520Z`, where both modes were pinned to `gpt-5.4` plus `xhigh` and `single_xhigh` won on both time and total tokens.
