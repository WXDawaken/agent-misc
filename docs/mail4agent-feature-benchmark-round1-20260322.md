# Mail4Agent Feature Benchmark Round 1

## Goal

Start a non-migration benchmark line for `mail4agent` by extending the existing Python mailbox product surface in three ways:

- inbox visibility
- routing explainability
- delivery audit evidence

## Selected Tasks

- `small_mail4agent_inbox_list_and_filters`
- `medium_mail4agent_routing_explain_surface`
- `large_mail4agent_delivery_audit_timeline`

## Shared Seed

- Template workspace: `E:\agent_misc\.tmp_test\mail4agent_feature_round1_20260322`
- Workspace manifest: `E:\agent_misc\benchmarks\mail4agent_feature_workspace_manifest.toml`

This shared seed keeps the repo in Python, carries no Rust scaffolding, and adds benchmark-only objective tests under `test/`.

## Run Policy

These three tasks should run as matched comparisons:

- `single_xhigh`
- `subagents`

The point of this round is to compare how both modes handle product-extension work, not language migration.

## Validation Entry Points

- `python -m unittest test.test_inbox_list_and_filters -v`
- `python -m unittest test.test_routing_explain_surface -v`
- `python -m unittest test.test_delivery_audit_timeline -v`

## Current Batch

- Results: `E:\agent_misc\benchmarks\results\20260322T082714Z`
- Analysis: `E:\agent_misc\benchmarks\results\20260322T082714Z\analysis.md`
- Dashboard: `http://127.0.0.1:8018`
- Total runs: `6`
- Objective status: all `6/6` runs passed validation
- First-pass outcome: `single_xhigh` was faster and used fewer total tokens on all three matched task pairs
- Blind judge bundle: `E:\agent_misc\benchmarks\results\20260322T100300Z_judge_packets`
- Blind judging status: all `3/3` public pairs scored
- Deblinded judged outcome: `single_xhigh` won `2/3` pair preferences and had the higher mean judged score
