# Engine and Salvage Run Cross-Project Tasks

## Intent

Use the new `game_engine/` plus `salvage_run/` split to define bounded cross-project tasks that are better A2A workloads than one-package-only edits.

These tasks are derived from concrete game-development needs that are visible in the current codebase, not from a generic desire to add more engine features.

## Current Gaps At The Engine Layer

The current `game_engine/` package is intentionally small. That is good for maintenance, but it means several game-development needs still live entirely inside `salvage_run/` or are not supported yet.

### 1. Structured Snapshot Contract

Missing today:

- no reusable engine-level snapshot shape for board state, HUD state, or messages
- no machine-readable layer contract for a future web or H5 client
- no stable serialization boundary between simulation and presentation

Why it matters:

- browser or H5 clients should not scrape console strings
- replay parity and snapshot tests are much easier once the shared contract is explicit

### 2. Command Catalog And Input Metadata

Missing today:

- no reusable command-spec model
- no engine-side place for aliases, argument shape, help text, or UI-facing command metadata
- `Salvage Run` still hand-rolls its command help and parsing rules

Why it matters:

- a future browser or H5 client needs the same command metadata as the console
- this is a good shared-core seam that stays small if we keep it declarative

### 3. Replay And Timeline Primitives

Missing today:

- no reusable engine-level replay/session runner
- no standard turn history or step result model
- scripted replay is still a CLI concern in `salvage_run.__main__`

Why it matters:

- replay is a natural validation and benchmark surface
- console, web, and later clients should share deterministic playback semantics

Status:

- completed in the mailbox-first `large_engine_replay_timeline` round
- `game_engine` now owns `run_command_replay(...)` plus replay-session dataclasses
- `salvage_run` now routes script replay through that shared runner with parity coverage

### 4. Theme And Symbol Abstraction

Missing today:

- no engine concept of theme, tile palette, or legend metadata
- no support for switching between ASCII and emoji/icon rendering
- no policy for Unicode-width-sensitive rendering

Why it matters:

- the current renderer can emit emoji text, but there is no supported theme layer
- future UI surfaces should not duplicate tile semantics in multiple places

Status:

- completed in the mailbox-first `medium_engine_theme_and_emoji_mode` round
- `game_engine` now owns `RenderTheme` and `RenderThemeSlot` plus ordered legend export and theme notes
- `salvage_run` now consumes that shared contract for ASCII and emoji themes and exposes explicit `--theme` CLI selection

### 5. Board Annotation And Inspection Metadata

Missing today:

- no shared representation for overlays, highlights, cell annotations, or inspector details
- no engine-owned way to express "this tile is hazardous", "this drone is in chase range", or "this cell is a point of interest"

Why it matters:

- console, web, and H5 surfaces will want richer board insight without rewriting gameplay rules
- this is the right place to support hover/select/inspect style UI later

Status:

- completed in the mailbox-first `large_engine_board_annotations` round
- `game_engine` now owns `SnapshotAnnotation` plus deterministic annotation serialization on `Snapshot`
- `salvage_run` now emits hazards, salvage, exit, drones, and player-centric inspection metadata through that shared contract

## Task Batch

Each task below is intentionally cross-project: one side changes `game_engine/`, and the other adapts `salvage_run/` to consume the new capability.

## Task 1: Shared Snapshot Contract

ID:

- `medium_engine_snapshot_contract`

Goal:

- add a reusable snapshot contract to `game_engine`
- make `salvage_run` export deterministic game snapshots without changing gameplay rules

Engine scope:

- add snapshot dataclasses or normalized dict helpers for:
  - board dimensions
  - tile layers
  - actor positions
  - messages
  - HUD or summary values
- keep the format plain-Python and JSON-serializable

Salvage Run scope:

- expose `GameState -> snapshot`
- cover board, HUD, messages, and terminal status
- add focused snapshot tests

Acceptance:

- console mode still works
- no gameplay behavior changes
- two runs with the same seed and commands produce the same snapshot sequence

Suggested focus paths:

- `E:\agent_misc\subagent_lab\game_engine`
- `E:\agent_misc\subagent_lab\salvage_run`
- `E:\agent_misc\subagent_lab\test`

Suggested validation:

```powershell
python -m unittest test.test_game_engine -v
python -m unittest test.test_salvage_run -v
```

## Task 2: Declarative Command Manifest

ID:

- `medium_engine_command_manifest`

Goal:

- move command metadata into a shared declarative layer
- keep `Salvage Run` rules game-specific while avoiding duplicated control/help definitions

Engine scope:

- add a compact command-spec model with:
  - command id
  - aliases
  - argument shape
  - description
  - optional UI label or hotkey hints
- add parser helpers that can consume the manifest

Salvage Run scope:

- define the `w/a/s/d`, `scan`, `dash`, `repair`, `wait`, `help`, and `quit` controls through the manifest
- generate help text from the shared definitions
- preserve existing command behavior

Acceptance:

- the command set and behavior remain backward-compatible
- the help text comes from one canonical definition source
- the resulting metadata would be usable by a future browser or H5 client

Suggested focus paths:

- `E:\agent_misc\subagent_lab\game_engine`
- `E:\agent_misc\subagent_lab\salvage_run\engine.py`
- `E:\agent_misc\subagent_lab\salvage_run\__main__.py`
- `E:\agent_misc\subagent_lab\test`

Suggested validation:

```powershell
python -m unittest test.test_game_engine -v
python -m unittest test.test_salvage_run -v
python -m salvage_run --script .\docs\salvage-run-example-script.txt --quiet-script
```

## Task 3: Shared Replay Timeline Runner

ID:

- `large_engine_replay_timeline`

Goal:

- add reusable replay/timeline primitives in `game_engine`
- move `Salvage Run` script replay onto that shared path

Engine scope:

- add a small session runner or transcript model for:
  - initial state
  - per-command step execution
  - step snapshots
  - terminal outcome
- keep the runner generic enough for turn-based games without inventing a full framework

Salvage Run scope:

- route script replay through the shared runner
- preserve the existing script file format
- add parity tests for final state and selected intermediate steps

Acceptance:

- console script mode still behaves the same from a user perspective
- replay sequences are deterministic
- the replay artifact is usable by future web or H5 playback

Suggested focus paths:

- `E:\agent_misc\subagent_lab\game_engine`
- `E:\agent_misc\subagent_lab\salvage_run\__main__.py`
- `E:\agent_misc\subagent_lab\salvage_run`
- `E:\agent_misc\subagent_lab\test`

Suggested validation:

```powershell
python -m unittest test.test_game_engine -v
python -m unittest test.test_salvage_run -v
python -m salvage_run --script .\docs\salvage-run-example-script.txt --quiet-script
```

## Task 4: Theme System With Emoji Mode

ID:

- `medium_engine_theme_and_emoji_mode`

Goal:

- add an engine-owned theme abstraction
- let `Salvage Run` offer an explicit `ascii` and `emoji` rendering mode

Engine scope:

- add theme or palette primitives for tile semantics and legend metadata
- optionally add width-safe helpers or documented limitations for Unicode output
- keep ASCII as the default path

Salvage Run scope:

- define a default ASCII theme plus one emoji theme
- thread the chosen theme through rendering
- add or document UTF-8 requirements where needed

Acceptance:

- default rendering remains unchanged
- emoji mode is opt-in
- no gameplay rules move into the renderer

Suggested focus paths:

- `E:\agent_misc\subagent_lab\game_engine`
- `E:\agent_misc\subagent_lab\salvage_run\ui.py`
- `E:\agent_misc\subagent_lab\salvage_run\__main__.py`
- `E:\agent_misc\subagent_lab\test`

Suggested validation:

```powershell
python -m unittest test.test_game_engine -v
python -m unittest test.test_salvage_run -v
```

### Note

This is a better task than "just add emoji" because it forces a real shared design boundary instead of a one-off UI tweak.

## Task 5: Inspectable Board Metadata

ID:

- `large_engine_board_annotations`

Goal:

- add a shared cell-annotation or overlay contract in `game_engine`
- make `Salvage Run` expose richer board semantics without baking UI inference into future clients

Engine scope:

- add a compact annotation model for:
  - terrain tags
  - actor tags
  - overlay flags
  - inspector-facing metadata
- keep it serializable and usable by both console and web surfaces

Salvage Run scope:

- annotate hazards, salvage, exit, drones, and chase-range-related facts
- expose selected-cell or tile-inspection metadata from the simulation side
- add tests for annotation contents

Acceptance:

- no gameplay rules change
- future clients can render overlays or inspectors from server-owned metadata instead of re-deriving it in JavaScript
- console mode still remains supported

Suggested focus paths:

- `E:\agent_misc\subagent_lab\game_engine`
- `E:\agent_misc\subagent_lab\salvage_run`
- `E:\agent_misc\subagent_lab\test`

Suggested validation:

```powershell
python -m unittest test.test_game_engine -v
python -m unittest test.test_salvage_run -v
```

## Recommended Order

If we want to use these as progressive collaboration tasks instead of one giant batch, the best order is:

1. `medium_engine_snapshot_contract`
2. `medium_engine_command_manifest`
3. `large_engine_replay_timeline`
4. `medium_engine_theme_and_emoji_mode`
5. `large_engine_board_annotations`

Why this order:

- snapshot and command metadata are the cleanest shared-core seams
- replay becomes easier once snapshots exist
- theme work is safer after the shared render contract is clearer
- board annotations are most valuable after snapshots already have a place to carry them

Current completion status:

- completed: `medium_engine_snapshot_contract`
- completed: `medium_engine_command_manifest`
- completed: `large_engine_replay_timeline`
- completed: `medium_engine_theme_and_emoji_mode`
- completed: `large_engine_board_annotations`
- remaining in this batch: none

## Why These Are Good A2A Tasks

Each task creates a real coordination boundary:

- one worker or one branch can own `game_engine/`
- another can adapt `salvage_run/`
- a reviewer can check for drift between shared contracts and gameplay behavior

That is a better collaboration probe than a purely local `salvage_run/` tweak, because the work naturally spans reusable primitives, game-specific adoption, tests, and docs.
