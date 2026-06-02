# Anchor Agent Protocol v0.1

## Scope

This document is the Phase 0 source of truth for the `anchor_agent` protocol.

The protocol covers:

- request and response envelopes
- core object IR
- initial action-related response shapes
- initial error codes

The protocol does not yet cover:

- action execution
- file mutation authority
- editor-side undo semantics
- streaming or push transport

## Transport

- HTTP + JSON
- default host: `127.0.0.1`
- default port: `37901`

## Protocol Version

All requests and responses in Phase 0 must use:

```json
"protocol_version": "0.1"
```

## Request Envelope

```json
{
  "protocol_version": "0.1",
  "request_id": "req_xxx",
  "session_id": "sess_xxx",
  "project_id": "godot_demo",
  "payload": {}
}
```

Field rules:

- `protocol_version`: required, must equal `"0.1"`
- `request_id`: required, request-scoped unique id
- `session_id`: optional for `/v1/session/open`, required for the rest
- `project_id`: required project or workspace identifier
- `payload`: endpoint-specific object payload

## Response Envelope

```json
{
  "protocol_version": "0.1",
  "request_id": "req_xxx",
  "ok": true,
  "error": null,
  "data": {}
}
```

## Error Envelope

```json
{
  "protocol_version": "0.1",
  "request_id": "req_xxx",
  "ok": false,
  "error": {
    "code": "INVALID_SNAPSHOT",
    "message": "Missing object_id",
    "details": {}
  },
  "data": null
}
```

## Initial Error Codes

- `INVALID_ENVELOPE`
- `INVALID_SNAPSHOT`
- `UNKNOWN_ACTION`
- `SESSION_NOT_FOUND`
- `OBJECT_NOT_FOUND`
- `EXECUTION_BOUNDARY_VIOLATION`
- `REQUEST_CLARIFICATION_REQUIRED`
- `UNSUPPORTED_PROTOCOL_VERSION`

## Core IR

### ObjectSnapshot

Required fields:

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

Initial capability examples:

- `move`
- `has_script`
- `has_collision_shape`
- `scene_editable`

### SuggestedAction

Required fields:

- `id`
- `title`
- `intent`
- `target_ids`
- `confidence`
- `risk`
- `requires_confirmation`
- `rationale`
- `preconditions`
- `tags`

### ActionPlan

Required fields:

- `action_id`
- `summary`
- `risk`
- `requires_confirmation`
- `steps`
- `affected_objects`
- `affected_files`
- `preview_changes`
- `preview_sections`
- `confirmation_details` when `requires_confirmation` is true
- `engine_mutations`
- `rollback_strategy`

`preview_sections` is a plugin-facing additive field for richer preview rendering.
Each section should contain:

- `id`
- `title`
- `lines`
- `style`

`confirmation_details` is a plugin-facing additive field for confirmation-required plans.
When present, it should contain:

- `reason`
- `review_items`

When `requires_confirmation` is `false`, omit `confirmation_details`.

### PatchProposal

Required fields:

- `patch_id`
- `action_id`
- `patch_kind`
- `target_id`
- `target_path`
- `format`
- `content`
- `apply_mode`

## Phase 0 Endpoints

### `POST /v1/session/open`

Open or reuse a session.

### `POST /v1/context/upsert`

Store or replace one or more snapshots for the session.

### `POST /v1/actions/suggest`

Return suggested actions for a target object already present in context.

### `POST /v1/actions/explain`

Explain why an action was suggested.

### `POST /v1/actions/plan`

Return a preview-only action plan.

### `POST /v1/actions/patch`

Return a preview patch proposal.

## Boundary Rules

- The Python core may suggest, explain, plan, and propose patches.
- The Python core may not mutate Godot state directly.
- The Godot plugin owns all real editor-side execution.
- Phase 0 and Phase 1 remain preview-only.
- If an action request is ambiguous about preview versus later plugin-local execution, for example with `execution_intent: "preview_or_execute"` or `requires_execution_clarification: true`, the core must reject it with `REQUEST_CLARIFICATION_REQUIRED`.
- If an action request asks for direct core-side execution, for example with `execution_intent: "apply"` or `allow_core_execution: true`, the core must reject it with `EXECUTION_BOUNDARY_VIOLATION`.
