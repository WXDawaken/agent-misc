# Salvage Run Web Port Workload

## Goal

Define a follow-on workload that is substantially more complex than the current console-only `Salvage Run` game while still being realistic for Codex CLI benchmark runs and native subagent experiments.

Recommended direction:

- port `Salvage Run` to a browser-playable web client
- preserve deterministic simulation and scripted replay behavior
- keep the Python game logic as the source of truth where practical

This is the preferred next large workload over a first-step Godot port.

## Why Web First

Compared with a Godot migration, a web port is a better benchmark target for this repo right now:

- easier to validate automatically with local commands and snapshot tests
- easier to inspect diffs because the core logic, JSON contracts, and UI are all plain text
- easier to decompose into bounded rounds for `explorer`, worker tiers, and `reviewer`
- less setup friction than introducing a full external game engine toolchain

Godot can still be a later escalation path if we want an even heavier workload after the web port is mature.

## Product Shape

The intended workload is not just "draw the board in HTML." It should exercise cross-file reasoning, architecture, UI state, replay flows, and validation.

Target experience:

- run a local web app for `Salvage Run`
- render the board, HUD, event log, and controls in the browser
- support keyboard or button-based commands
- support scripted replay from the existing command-script format
- keep deterministic parity with the console simulation for the same seed and scripted inputs
- expose enough testable state that validation can stay mostly automated

## Recommended Architecture

Prefer a shared-core design instead of duplicating gameplay logic in JavaScript.

Suggested shape:

- keep the Python simulation as the source of truth for rules, AI, scoring, and command resolution
- treat the new `game_engine/` package as the reusable base and `salvage_run/` as the game-specific layer
- extract a stable state-to-JSON snapshot layer from the current console game
- add a small web-serving layer that can run locally
- build a browser client that renders snapshots and submits commands

Suggested repository shape:

- `salvage_run/`
  - Salvage Run rules, levels, UI, replay helpers
- `game_engine/`
  - shared grid, rendering, and turn-loop primitives
- `salvage_run_web/`
  - local server entrypoint
  - request handlers or simple API endpoints
  - static asset serving
- `web/`
  - `index.html`
  - `app.js`
  - `styles.css`
- `test/`
  - console tests
  - JSON snapshot/contract tests
  - replay parity tests
  - light server tests where practical

## Complexity Drivers

This workload is intentionally large because it forces several kinds of coordination at once:

- shared-core refactoring so console and web modes do not drift
- explicit JSON contract design for board state, HUD values, messages, and terminal outcomes
- front-end rendering and browser-side input handling
- server or local bridge behavior for command submission and replay
- replay parity validation between console and web output paths
- docs and run-command updates

That combination makes it a strong benchmark target for when subagents should outperform a single agent through isolation and parallelism.

## Scope Boundaries

To keep the workload hard but still benchmarkable, the first version should avoid unnecessary engine work.

Include:

- board rendering in the browser
- HUD with energy, hull, salvage, score, turn, and map name
- event log rendering
- command buttons plus keyboard input
- scripted replay mode in the browser
- clear terminal-state presentation for win, loss, quit, and unfinished script

Avoid in the first version:

- real-time movement or animation-heavy game feel
- multiplayer
- networked persistence
- account systems
- procedural graphics pipelines
- Godot-specific scene work

## Proposed Milestones

### Milestone 1: Shared Snapshot Contract

Extract a deterministic snapshot layer from the existing game.

Deliverables:

- Python API that returns a complete serializable game snapshot
- tests for snapshot shape and deterministic contents
- docs for the snapshot contract

Why it is useful:

- creates a clean handoff boundary between simulation and UI
- already valuable for richer console testing and replay tooling

### Milestone 2: Local Web Shell

Add a minimal local web app that can render one snapshot and submit commands.

Deliverables:

- local server entrypoint
- browser board rendering
- HUD and event log
- command submission loop

Why it is useful:

- establishes the end-to-end path without requiring a full UI redesign

### Milestone 3: Script Replay Parity

Bring the existing script format to the browser path.

Deliverables:

- replay loader for existing script files
- step or autoplay controls
- parity checks between console and web final states

Why it is useful:

- makes validation much stronger
- creates a benchmark-friendly repeatable scenario

### Milestone 4: Interaction Polish

Improve usability without changing gameplay rules.

Deliverables:

- selected-cell or hover telemetry
- clearer chase-range, hazard, or salvage visualization
- better end-of-run summary presentation

Why it is useful:

- introduces meaningful UI complexity after the core architecture is stable

## Benchmark Task Ideas

This larger workload can supply several benchmark scales instead of only one oversized project.

### Small

- add JSON snapshot fields for one new HUD concept
- add replay status text in the web UI
- add one focused UI indicator such as chase-range highlighting

### Medium

- implement script replay controls in the browser
- add parity validation for console vs web final summaries
- add an inspector panel for the selected tile or entity

### Large

- deliver the first end-to-end browser-playable port
- refactor the Python core so console and web modes share one command-resolution contract
- add a deterministic replay viewer with final-state parity checks

## Validation Strategy

The workload should remain automatable from the CLI.

Recommended validation layers:

- unit tests for game-state and snapshot serialization
- replay parity tests comparing console and web-facing final states
- light server tests for command submission and snapshot endpoints
- optional HTML or asset smoke checks if the web shell is static enough

Example command shape:

```powershell
python -m unittest test.test_salvage_run -v
python -m unittest test.test_salvage_run_web -v
```

If a local server entrypoint exists later, keep it scriptable and smoke-testable from the CLI.

## Why This Is Good For Subagents

This workload gives each role a clear reason to exist:

- `explorer`
  - map the current console architecture
  - identify extraction seams and state-contract risks
- `worker_low`
  - local UI or snapshot-field additions
  - test-only or docs-only companion work
- `worker`
  - bounded server or browser feature slices
  - moderate replay or contract changes
- `worker_high`
  - shared-core extraction across `game_engine`, `salvage_run`, and web layers
  - parity-sensitive changes spanning simulation, transport, UI, and tests
- `reviewer`
  - catch drift between console and web behavior
  - check missing parity coverage and replay validation gaps

This is exactly the kind of workload where context isolation should become more valuable than in the current small console game.

## Why Not Start With Godot

Godot is still a good future stretch goal, but it is a weaker next step for this repo right now:

- heavier external toolchain dependency
- harder automated validation in the benchmark harness
- more binary or editor-generated churn
- less transparent diffs for early benchmark comparisons

Recommendation:

- use the web port as the next complex benchmark workload
- consider a later Godot client only after the web snapshot and replay contracts are stable

## Suggested Prompt For Future Runs

```text
Use the repo's main-agent routing workflow on the Salvage Run web-port workload.
Keep the Python simulation as the source of truth unless the task explicitly changes architecture.
Prefer bounded rounds that preserve console/web parity and add verification evidence.
```
