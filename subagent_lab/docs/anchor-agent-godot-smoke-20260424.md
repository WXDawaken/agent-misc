# Anchor Agent Godot Smoke

Date: `2026-04-24`

## Purpose

Record the first local Godot environment setup, the thin editor-load smoke, and the first visible editor selection smoke for the `anchor_agent` plugin.

This is an experiment-environment note, not a product milestone.

## Godot Install

- Installed as a portable local tool under `E:\agent_misc\tools\godot-4.6.2`.
- Verified binary: `E:\agent_misc\tools\godot-4.6.2\Godot_v4.6.2-stable_win64_console.exe`.
- Verified version: `4.6.2.stable.official.71f334935`.
- Source: official Godot Windows download page, current stable `4.6.2`.

## Headless Editor Smoke

Created a temporary Godot project at `E:\agent_misc\.tmp_godot_anchor_smoke_fixed` with:

- `project.godot`
- `addons/anchor_agent/` copied from the repo plugin shell
- plugin enabled via `res://addons/anchor_agent/plugin.cfg`

Command:

```powershell
& 'E:\agent_misc\tools\godot-4.6.2\Godot_v4.6.2-stable_win64_console.exe' --headless --editor --path 'E:\agent_misc\.tmp_godot_anchor_smoke_fixed' --quit --log-file 'E:\agent_misc\.tmp_godot_anchor_smoke_fixed\godot-headless-editor.log'
```

Result:

- Godot editor initialization completed in headless mode.
- The plugin reached the editor plugin initialization phase without script-load errors after fixing `plugin.cfg`.

## Visible Editor Selection Smoke

Created a second temporary Godot project at `E:\agent_misc\.tmp_godot_anchor_visible_smoke` with:

- `project.godot`
- `scenes/selection_smoke.tscn`
- `addons/anchor_agent/` copied from the repo plugin shell
- plugin enabled via `res://addons/anchor_agent/plugin.cfg`

The scene contains:

- `SelectionSmokeRoot`
- `PlayerWithCollision` as `CharacterBody3D`
- `CollisionShape3D` under `PlayerWithCollision`
- `PlayerWithoutCollision` as `CharacterBody3D`

Headless preflight command:

```powershell
& 'E:\agent_misc\tools\godot-4.6.2\Godot_v4.6.2-stable_win64_console.exe' --headless --editor --path 'E:\agent_misc\.tmp_godot_anchor_visible_smoke' --quit --log-file 'E:\agent_misc\.tmp_godot_anchor_visible_smoke\godot-preflight.log'
```

Visible editor launch command:

```powershell
Start-Process -FilePath 'E:\agent_misc\tools\godot-4.6.2\Godot_v4.6.2-stable_win64.exe' -ArgumentList @('--editor','--path','E:\agent_misc\.tmp_godot_anchor_visible_smoke')
```

Result:

- The Godot editor opened the temporary project and `selection_smoke.tscn`.
- The Anchor Agent dock registered as `AgentDock` in the Godot editor layout.
- The `AgentDock` tab was visible and showed `Anchor Agent Preview`.
- Selecting `PlayerWithoutCollision` updated the dock with the selected node name, type, editor path, and scene path.
- Selecting `PlayerWithCollision` also updated the dock with the selected node name, type, editor path, and scene path.
- Local evidence files were captured under the temporary project, including `godot-visible-smoke-agentdock.png` and `godot-visible-smoke-selection-info.png`.

This confirms the current plugin shell is no longer only fixture-inspectable: a real Godot editor session can load the plugin dock and drive the selection-change display path.

## Finding

The first smoke exposed that `plugin.cfg` used:

```ini
script="res://addons/anchor_agent/plugin.gd"
```

Godot treated that as relative to the plugin config location during editor plugin loading and attempted to load:

```text
res://addons/anchor_agent/res:/addons/anchor_agent/plugin.gd
```

The plugin now uses:

```ini
script="plugin.gd"
```

`anchor_agent.test.test_phase0_assets.AnchorAgentPhase0Tests.test_plugin_shell_files_exist` now asserts this so future fixture-only tests catch the same issue earlier.

## MCP Readout

Godot MCP tooling looks useful for later automation, but not as the first live smoke dependency.

Useful capabilities from current Godot MCP options include:

- project and filesystem inspection
- scene tree inspection
- editor or game screenshots
- Godot errors and output logs
- optional scene/node manipulation

Recommendation:

- First run a manual or semi-manual live editor smoke to validate dock visibility and selection-change behavior.
- Then consider MCP for repeatable observation, logs, screenshots, and scene-tree state capture.
- Do not let MCP replace the core/plugin boundary under test: `anchor_agent` still needs its own plugin snapshot path and core planning protocol.

## Remaining Smoke Gaps

The first visible editor smoke covered dock visibility and selected-node target summary updates.

Remaining live-editor checks:

- empty selection resets stale action and preview state
- a selected `CharacterBody3D` with and without a collision child produces the expected snapshot capability difference through the full plan-preview path
