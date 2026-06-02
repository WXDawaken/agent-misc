# Anchor Agent Selection Lifecycle Probe 2026-04-02

## Sample

- `positive_plugin_selection_lifecycle_probe`

## Intent

Add one more realistic plugin-side lifecycle seam without forcing a full live Godot editor smoke.

The goal was to check whether the current mailbox-first split still behaves well when the task moves from fixture-only rendering toward editor-selection lifecycle behavior.

## Scenario

- Send an editor-facing request to `plugin_dev`.
- Ask for the dock to react to selection changes:
  - rebuild a plugin-local snapshot for the selected node
  - update the target summary when selection changes
  - reset the dock to the empty state when no node is selected
- Keep the request local unless a concrete missing core contract appears.

## Observed Outcome

- Thread: `9cb15bc2-ad67-4d82-9672-8ea00a40141e`
- Request message: `23790520-67f1-4afe-bca7-5c9f9df28454`
- Reply message: `e43e505a-9889-4dd7-b8b3-ddcc71ec117c`

`plugin_dev` handled the request directly and replied with:

- `task_status: "completed"`
- changed files limited to:
  - `anchor_agent/anchor_agent_godot_plugin/addons/anchor_agent/plugin.gd`
  - `anchor_agent/anchor_agent_godot_plugin/addons/anchor_agent/ui/agent_dock.gd`
  - `anchor_agent/test/test_phase0_assets.py`

## What Landed

- `plugin.gd` now connects to `EditorSelection.selection_changed`
- the plugin uses the existing `selection_adapter.gd` plus `snapshot_builder.gd`
- when a node is selected:
  - the plugin builds a snapshot
  - the dock shows a selection-oriented summary
- when selection is empty or snapshot building yields no data:
  - the dock resets to its empty state
  - stale actions and preview text are cleared

## Validation

- `python -m unittest anchor_agent.test.test_phase0_assets.AnchorAgentPhase0Tests.test_plugin_selection_lifecycle_wiring_exists anchor_agent.test.test_phase0_assets.AnchorAgentPhase0Tests.test_plugin_empty_state_copy_is_descriptive anchor_agent.test.test_phase0_assets.AnchorAgentPhase0Tests.test_plugin_dock_mentions_preview_sections -v`
- `python -m unittest discover -s anchor_agent\\test -v`
- `python -m unittest discover -v`

## Boundary Evidence

- `core_dev` stayed idle for the round:
  - on-call summary ended with `processed = 0`
- no core or protocol files changed
- no mailbox request was sent to `core_dev`

## Conclusion

This probe behaved as intended.

It is not a full live-editor smoke, but it does move the environment one step closer to a real Godot lifecycle by wiring the dock to selection changes in repo-visible code. Just as importantly, it showed that a more realistic editor-facing task can still stay local to `plugin_dev` without unnecessary escalation.
