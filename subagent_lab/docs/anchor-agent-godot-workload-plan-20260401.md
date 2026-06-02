# Anchor Agent Godot Workload Plan

## Goal

Evaluate the Godot `anchor_agent` proposal as a new A2A collaboration environment that complements `Salvage Run` instead of replacing it.

The target is not a polished Godot product. The target is a bounded two-project workload that exposes:

- protocol ownership versus consumer ownership
- planner versus executor boundaries
- when a role should escalate to the other side
- when a role should refuse or defer work
- multi-round mailbox coordination on top of a typed API seam

## Why This Environment Is Worth Adding

Compared with `Salvage Run`, this proposal changes the collaboration shape in useful ways:

- It has a hard split between a Python `core` and a Godot `plugin`.
- It is protocol-first, with explicit request and response envelopes plus typed IR.
- It has a stronger execution boundary: the core may suggest and plan, but only the plugin may mutate editor state.
- It introduces a real "consumer plus service" seam instead of an engine-plus-game seam.
- It should generate both positive and negative A2A samples without needing a large codebase.

## Environment Shape

Treat this as a new nested workload under `subagent_lab`, parallel to `Salvage Run`.

Suggested structure:

```text
anchor_agent/
  anchor_agent_core/
  anchor_agent_godot_plugin/
  test_fixtures/
  docs/
```

Project roles:

- `core_dev`
- `plugin_dev`
- optional `protocol_owner` later if schema churn becomes a bottleneck

The default mailbox front door should be `plugin_dev`, because user-visible workflow starts from editor selection and plugin-owned execution.

## Scope Cuts For Experiment Use

Keep the proposal, but narrow it for A2A signal quality.

Keep:

- `FastAPI` plus `pydantic` core
- `EditorPlugin` plus `HTTPRequest` Godot plugin
- typed `ObjectSnapshot`, `SuggestedAction`, `ActionPlan`, and `PatchProposal`
- selection-driven workflow
- action suggestion and plan preview
- explicit "core suggests, plugin executes" boundary

Defer:

- free chat
- automatic execution
- broad scene mutation
- overlays and rich editor chrome
- cross-scene batch operations
- model-backed planning

## Recommended Phase 0

Before the proposal's existing Phase 1, add a benchmark-friendly Phase 0:

1. Freeze the protocol envelope and IR in one doc and one fixture set.
2. Create a handful of static `ObjectSnapshot` JSON fixtures.
3. Define golden responses for `suggest`, `explain`, and `plan`.
4. Decide one tiny Godot manual smoke path, but keep most validation fixture-driven.

This keeps environment failures from being dominated by editor setup noise.

## A2A-First Delivery Order

### Phase 1: Protocol And Core Skeleton

Deliver:

- `anchor_agent_core` project scaffold
- request and response envelope types
- IR types
- in-memory session and context store
- rule-based planner
- `POST /v1/session/open`
- `POST /v1/context/upsert`
- `POST /v1/actions/suggest`

Primary collaboration value:

- protocol definition ownership
- plugin-facing API stability
- core-only local implementation with bounded review from plugin side

### Phase 2: Fixture-Driven Plugin Client

Deliver:

- `anchor_agent_godot_plugin` scaffold
- `core_client.gd`
- `snapshot_builder.gd`
- dock UI shell
- fixture-backed request and response rendering

Primary collaboration value:

- plugin side can consume the agreed protocol without needing full live editor behavior first
- forces negotiation around snapshot shape and missing fields

### Phase 3: Plan Preview Loop

Deliver:

- `/actions/explain`
- `/actions/plan`
- `/actions/patch`
- action click to preview path in the dock

Primary collaboration value:

- richer cross-project iteration
- more chances for "plugin asks for missing fields" and "core narrows plan semantics"

### Phase 4: Minimal Live Godot Smoke

Deliver:

- selection changed hook
- real snapshot build for one or two node kinds
- one manual smoke path in Godot editor

Primary collaboration value:

- validates the environment is real without making editor automation the main workload

### Phase 5: Execution Skeleton Only

Deliver:

- `engine_executor.gd`
- `undo_bridge.gd`
- no actual mutation flow yet beyond stubs

Primary collaboration value:

- tests whether both roles preserve the execution boundary instead of prematurely implementing unsafe automation

## Positive A2A Sample Ideas

Good collaboration tasks for this environment:

- `plugin` discovers the snapshot lacks one capability flag and escalates a protocol change request to `core`
- `core` adds a new suggested action, then `plugin` adopts new display metadata
- `plugin` requests a more preview-friendly `ActionPlan` field and `core` extends the protocol
- both sides coordinate on `CharacterBody3D` rule coverage without breaking the execution boundary

## Negative A2A Sample Ideas

This environment should also produce strong "do not collaborate" or "defer" samples:

- plugin-only dock wording or layout tweak should not escalate to `core_dev`
- core-side planner wording change should not require `plugin_dev`
- request to let core edit scene state should be rejected or deferred as boundary-violating
- ambiguous request about whether an action should execute or only preview should move to `waiting_on_requester`
- schema churn should not happen if an existing field is already sufficient

## Why It Complements Salvage Run

`Salvage Run` is strongest at:

- reusable seam extraction
- consumer adoption
- positive and negative cross-project mailbox routing
- lightweight Python-only validation

`anchor_agent` would be strongest at:

- protocol ownership
- service-consumer coordination
- strict execution-boundary discipline
- typed preview contracts
- UI plus service evolution across a non-Python boundary

That makes it a better second environment than simply extending the game further.

## Recommendation

Use this proposal as the next environment candidate, but do not start from the full product ask.

Recommended next step:

1. Create a new `anchor_agent` workspace inside `subagent_lab`.
2. Land Phase 0 fixtures plus Phase 1 core skeleton.
3. Treat the Godot plugin as a consumer project, not the initial source of truth.
4. Add mailbox roles only after the protocol and fixture surface are stable enough to avoid role confusion.

## Open Questions

- Whether Phase 2 should initially use a plain GDScript consumer harness before a full dock scene.
- Whether `protocol_owner` should exist as a distinct mailbox role, or whether the coordinator can absorb protocol arbitration.
- Whether this workload belongs in the benchmark harness before or after the first manual Godot smoke path is working.
- Whether the first benchmark batch should compare `Salvage Run` and `anchor_agent` directly, or keep them as separate tracks until both have one positive and one negative sample batch.
