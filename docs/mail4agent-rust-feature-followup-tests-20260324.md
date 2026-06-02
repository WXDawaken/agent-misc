# Mail4Agent Rust Feature Follow-up Tests

## Goal

Turn the current bridge observations into a cleaner next batch.

The current hypothesis is:

- `single_xhigh` is still strongest on bounded Rust feature-port work
- `subagents` become more competitive when the task has hidden contracts, operator-facing quality surface, or enough side questions to diffuse a single serial solve path

So the next batch should test task shape, not just task size.

## Current Read To Test

What we want to distinguish next:

1. Is the `subagents` judged advantage specific to bridge-like subprocess integration?
2. Or does it generalize to any large Rust task with hidden quality surface?
3. Where is the threshold where bounded `single_xhigh` stops being the cleaner default?

## Selected Next Tests

### 1. `large_mail4agent_rust_export_import_environment_bundle`

Role:

- large non-bridge control

Why this test:

- it is still large and cross-cutting
- but it is more schema, serialization, and API-shape heavy than subprocess-bridge heavy
- it should have less hidden runtime contract than the bridge task

Expected value:

- if `single_xhigh` wins both objective and judged here, that supports the idea that the current bridge pattern is not a general large-task rule
- if judged still leans `subagents`, then the pattern is probably broader than bridge alone

### 2. `large_mail4agent_rust_delivery_audit_timeline`

Role:

- large hidden-quality non-bridge integration control

Why this test:

- it is already implemented and benchmarked on the Python feature line, so it has a clean semantic oracle for Rust porting
- it is operator-trust and evidence heavy without depending on the bridge subprocess path
- it stresses schema evolution, lifecycle evidence, and operator-facing explanation, which makes it a good control for the "attention diffusion" hypothesis outside the bridge lane

Expected value:

- if judged leans `subagents` here too, then the mechanism is likely about hidden quality surface and attention control, not bridge-specific code paths
- if `single_xhigh` wins cleanly here, then the current bridge split is probably more task-specific

### 3. `medium_mail4agent_rust_routing_explain_surface`

Role:

- medium explanatory-surface control

Why this test:

- it has hidden clarity requirements but is not as cross-cutting as the large tasks
- it checks whether explanation and evidence surfaces alone are enough to trigger the same pattern
- it also gives us a non-bridge, non-operator task that still rewards careful contract reading

Expected value:

- if `single_xhigh` still wins here, that supports the idea that size plus integration breadth matters
- if judged flips toward `subagents`, then the bridge pattern may be partly about explanation/evidence quality rather than only task breadth

## Execution Policy

- Use the explicit-config harness so both modes are pinned to `gpt-5.4 + xhigh`.
- Keep the benchmark-scoped isolated `CODEX_HOME`.
- Use stabilized seeds and keep the explicit single-thread prompt for `single_xhigh`.
- Start with one paired replicate for each task.
- Only add blind judged passes after objective results are in, because the main purpose of this batch is task-shape discrimination.
- Do not add more bridge replicates until this batch is done; right now the bridge task already has enough evidence to motivate a control batch.

## Decision Rules

After these three tests:

- If export/import and routing-explain both favor `single_xhigh`, while delivery-audit judged favors `subagents`, then the real split is likely "hidden quality surface" rather than bridge alone.
- If all three favor `single_xhigh`, then the current bridge pattern is probably more task-specific than general.
- If both large non-bridge tasks also judged-favor `subagents`, then we should treat `subagents` as a serious default candidate for large Rust feature-port integration work, even if objective winners remain mixed.

## Status

This is a test slate only.

The tasks are selected and ordered, but not yet materialized into a new benchmark batch.
