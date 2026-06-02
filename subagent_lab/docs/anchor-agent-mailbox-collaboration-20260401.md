# Anchor Agent Mailbox Collaboration

## Intent

Define a mailbox-first collaboration split between the `anchor_agent_core` service and the `anchor_agent_godot_plugin` consumer.

## Roles

- `plugin_dev`
  - front door for editor-facing workflow and dock UX requests
  - owns `E:\agent_misc\subagent_lab\anchor_agent\anchor_agent_godot_plugin\`
  - owns plugin-facing validation and fixture adoption inside `E:\agent_misc\subagent_lab\anchor_agent\test\`
- `core_dev`
  - owns protocol, planner, and core API behavior
  - owns `E:\agent_misc\subagent_lab\anchor_agent\anchor_agent_core\`
  - owns `E:\agent_misc\subagent_lab\anchor_agent\docs\protocol-v0_1.md`
  - owns core-facing fixtures under `E:\agent_misc\subagent_lab\anchor_agent\test_fixtures\`

## Boundary

- `plugin_dev` must not edit `anchor_agent_core/`
- `core_dev` must not edit `anchor_agent_godot_plugin/`
- plugin-driven protocol needs should be turned into bounded mailbox requests instead of cross-editing the other project

## Routing Rule

- send editor-facing or dock-facing requests to `plugin_dev` first
- only send work to `core_dev` when `plugin_dev` identifies a bounded missing core contract, preview field, or planner behavior

## Progress Tracking

- each on-call reply should include an explicit `task_status`
- use mailbox-native status updates instead of guessing completion from silence
- treat `waiting_on_peer` as the normal state after `plugin_dev` requests a bounded contract addition from `core_dev`
- if a role receives only a terminal completion or deferral notice after its own thread state is already terminal, it should absorb that delivery without sending another no-op completion reply

## Why This Helps

- it creates a real service-consumer seam instead of letting one agent edit both sides of the protocol
- it makes protocol growth explicit and reviewable
- it tests whether `plugin_dev` can request just enough new preview surface without turning `core_dev` into an executor
