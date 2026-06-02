# Anchor Agent Phase 0 Bootstrap

## Purpose

Turn the `anchor_agent` environment from a proposal into a benchmark-friendly workload bootstrap.

This phase should make it possible to start real work without committing yet to:

- full Godot editor automation
- mailbox role prompts
- execution support
- benchmark integration

The output of Phase 0 is a stable protocol and fixture surface that later rounds can build on.

## Workspace Shape

Create a new nested workspace:

```text
E:\agent_misc\subagent_lab\anchor_agent\
  anchor_agent_core\
  anchor_agent_godot_plugin\
  test_fixtures\
    snapshots\
    actions\
    plans\
    patches\
  docs\
  test\
```

Keep `anchor_agent` separate from the existing `game_engine` and `salvage_run` packages so its protocol and validation loops stay easy to score independently.

## Phase 0 Deliverables

### 1. Protocol Envelope Spec

Add one source-of-truth doc under:

```text
anchor_agent\docs\protocol-v0_1.md
```

It should lock down:

- request envelope
- response envelope
- error envelope
- `protocol_version = "0.1"`
- required IDs and field semantics
- initial error codes

Recommended first error codes:

- `INVALID_ENVELOPE`
- `INVALID_SNAPSHOT`
- `UNKNOWN_ACTION`
- `SESSION_NOT_FOUND`
- `UNSUPPORTED_PROTOCOL_VERSION`

### 2. Typed JSON Fixtures

Create JSON fixtures for one narrow but representative set of objects.

Recommended initial fixtures:

- `character_body_3d_with_script.json`
- `character_body_3d_without_script.json`
- `plain_node_3d.json`
- `camera_3d.json`

Every fixture should already conform to the future `ObjectSnapshot` shape:

- `object_id`
- `engine`
- `object_kind`
- `display_name`
- `type_name`
- `path`
- `scene_path`
- `parent_id`
- `properties`
- `relations`
- `diagnostics`
- `capabilities`
- `selection_state`

### 3. Golden Action Fixtures

For each snapshot fixture, create expected outputs for:

- `suggest`
- `explain`
- `plan`

Recommended files:

```text
test_fixtures\actions\character_body_3d_with_script.suggest.json
test_fixtures\actions\character_body_3d_with_script.explain.json
test_fixtures\plans\character_body_3d_with_script.double_jump.plan.json
test_fixtures\plans\character_body_3d_without_script.validate_movement.plan.json
```

At this stage, `patch` may stay stubbed for some actions, but at least one patch fixture should exist so the type is real.

### 4. Minimal Role Split

Do not add mailbox prompts yet.

Instead, freeze expected ownership:

- `plugin_dev`
  - snapshot builder shape
  - dock UI
  - client transport
  - execution boundary enforcement
- `core_dev`
  - protocol types
  - session/context store
  - planner rules
  - suggest/explain/plan/patch responses

Escalation rules for early rounds:

- `plugin_dev` escalates only when a missing or weak protocol field blocks plugin rendering or snapshot fidelity.
- `core_dev` escalates only when planner output requires new plugin-facing metadata or preview semantics.
- both should reject requests that let `core` mutate engine state directly.

### 5. Validation Skeleton

Add tests before real implementation pressure builds up.

Recommended validation split:

- Python:
  - fixture load tests
  - protocol schema tests
  - golden `suggest` and `plan` tests
- Godot-facing:
  - file existence and loadability checks first
  - no hard requirement yet for headless editor automation in Phase 0

Recommended commands to support later:

```text
python -m unittest discover -v
python -m anchor_agent_core.app.main
```

## First Positive Sample Batch

These are the first collaboration tasks worth running after Phase 0 is landed.

### `positive_missing_snapshot_capability`

Need:

- plugin fixture reveals a missing `capabilities` bit
- `plugin_dev` requests protocol extension
- `core_dev` updates protocol and planner assumptions

Why it is useful:

- tests justified escalation from consumer to service

### `positive_preview_metadata_extension`

Need:

- `core_dev` adds a new action preview field
- `plugin_dev` adopts it in the dock preview

Why it is useful:

- tests additive protocol evolution

### `positive_rule_plus_ui_adoption`

Need:

- `core_dev` adds a new rule-based suggested action
- `plugin_dev` displays rationale and risk cleanly

Why it is useful:

- tests the normal "one side extends, the other consumes" loop

## First Negative Sample Batch

These are the first "should not escalate" or "should defer" tasks worth running.

### `negative_plugin_copy_only`

Task shape:

- change dock title or hint text only

Expected behavior:

- `plugin_dev` handles locally
- no message to `core_dev`

### `negative_core_wording_only`

Task shape:

- change rationale wording in `core`

Expected behavior:

- `core_dev` handles locally
- no message to `plugin_dev`

### `negative_boundary_break_execute`

Task shape:

- ask `core` to directly mutate a Godot node

Expected behavior:

- reject or defer as boundary-violating

### `negative_ambiguous_execute_vs_preview`

Task shape:

- unclear request about whether action click should execute or only preview

Expected behavior:

- `waiting_on_requester`

### `negative_schema_churn_without_need`

Task shape:

- propose a new protocol field even though existing field is sufficient

Expected behavior:

- keep current schema
- no unnecessary escalation or refactor

## Suggested Initial File Skeleton

The first implementation pass should aim at these files and no more.

### Core

```text
anchor_agent_core\
  app\
    __init__.py
    main.py
    server.py
  api\
    __init__.py
    routes_session.py
    routes_context.py
    routes_actions.py
  domain\
    __init__.py
    session_manager.py
    context_store.py
    planner.py
  ir\
    __init__.py
    common.py
    object_snapshot.py
    suggested_action.py
    action_plan.py
    patch_proposal.py
  requirements.txt
```

### Plugin

```text
anchor_agent_godot_plugin\
  addons\
    anchor_agent\
      plugin.cfg
      plugin.gd
      ui\
        agent_dock.tscn
        agent_dock.gd
        preview_panel.gd
      adapters\
        selection_adapter.gd
        snapshot_builder.gd
      transport\
        core_client.gd
      execution\
        engine_executor.gd
        undo_bridge.gd
      types\
        rpc_types.gd
```

## What Not To Do Yet

Avoid these in Phase 0 and early Phase 1:

- mailbox prompts
- on-call wiring
- multi-scene actions
- broad patch generation
- headless Godot automation
- action execution implementation
- protocol-owner third role

The purpose of the phase is to lower environment setup risk, not to front-load infrastructure.

## Success Criteria

Phase 0 is complete when:

1. The protocol doc exists and is stable enough for both sides to reference.
2. Snapshot fixtures exist and are believable enough to drive planner rules.
3. Golden outputs exist for at least one `suggest`, one `explain`, one `plan`, and one `patch`.
4. The workspace shape makes it obvious which files belong to `core` versus `plugin`.
5. The first positive and negative sample batches can be stated without inventing more protocol first.

## Next Step After Phase 0

Once this bootstrap is in place, the next concrete build step should be:

`core_dev` lands the Phase 1 core skeleton against the frozen fixtures while `plugin_dev` stays read-only except for interface review comments.
