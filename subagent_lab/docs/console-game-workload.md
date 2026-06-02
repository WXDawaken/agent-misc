---
id: console-game-workload
title: Console Game Workload
type: guide
workspace: subagent_lab
domains:
  - workload
  - salvage-run
  - game-engine
status: reference
created: 2026-03-19
updated: 2026-03-31
summary: Describe the Salvage Run gameplay workload, how to run it, and why it is useful for native subagent experiments.
related:
  - codex-native-subagents
supersedes: []
artifact_paths: []
---

# Console Game Workload

Describe the reusable engine plus `Salvage Run` game workload that native subagents use for real multi-file coding tasks, validation, and prompt experiments.

## Index

- [Paths](#paths)
- [Run](#run)
- [Test](#test)
- [Gameplay](#gameplay)
- [Good Subagent Tasks](#good-subagent-tasks)
- [Suggested Native Subagent Prompt](#suggested-native-subagent-prompt)

This repo includes two related Python projects:

- `game_engine`: a small reusable Python grid/turn engine
- `salvage_run`: the `Salvage Run` game built on top of that engine

It is here for two reasons:

- to give Codex native subagents a real multi-file codebase to inspect and modify
- to provide a repeatable workload with gameplay rules, state transitions, and tests

## Paths

- Engine package: `E:\agent_misc\subagent_lab\game_engine`
- Game package: `E:\agent_misc\subagent_lab\salvage_run`
- Tests: `E:\agent_misc\subagent_lab\test\test_game_engine.py`, `E:\agent_misc\subagent_lab\test\test_salvage_run.py`

## Run

```powershell
python -m salvage_run
python -m salvage_run --seed 1
python -m salvage_run --script .\docs\salvage-run-example-script.txt
python -m salvage_run --script .\docs\salvage-run-example-script.txt --quiet-script
```

## Test

```powershell
python -m unittest test.test_salvage_run -v
```

## Gameplay

- Move with `w`, `a`, `s`, `d`
- `dash <dir>` spends 3 energy to move up to 2 tiles in one turn, but a blocked dash costs 1 hull
- `scan` reports nearby salvage, drones, exit distance, whether the nearest drone is in or out of chase range, and how many drones are currently in chase range
- `repair` spends 3 energy to restore 1 hull
- `wait` spends a turn without moving
- `help` prints controls
- `quit` exits the run
- Drones now idle around their patrol posts when you are far away, then switch to direct pursuit at 4 steps or closer
- `--script <path>` replays commands from a text file; blank lines and `#` comments are ignored
- `--quiet-script` works with `--script` to suppress per-turn snapshots and command echoes while keeping final state and outcome output
- Script replay now runs through a shared `game_engine.run_command_replay(...)` contract, so replay artifacts and playback semantics can be reused by future non-console clients
- Shared snapshots now carry optional engine-owned board annotations, so future console or web inspectors can consume hazard, salvage, exit, drone, and player-centric metadata without re-deriving those facts from UI strings
- Rendering themes now run through shared `game_engine` theme contracts; `--theme ascii` remains the default and `--theme emoji` is opt-in
- When a non-ASCII theme is selected, the CLI now reconfigures stdout/stderr to UTF-8 so emoji script mode works in the local Windows shell
- Score is shown in the status line each turn and is computed from salvage collected, remaining energy, remaining hull, and turns taken

Goal:

- collect enough salvage crates
- then reach the exit shuttle
- survive drone hits and battery drain on the way

## Good Subagent Tasks

This workload is intentionally small but non-trivial. Good follow-up tasks include:

- extract or refine another reusable engine primitive without over-abstracting the game
- rebalance `dash` risk versus reward
- rebalance drone behavior
- rebalance score formula weights
- add another map template
- improve rendering or event messages
- fix or extend tests

For cross-project tasks that explicitly span `game_engine/` and `salvage_run/`, see:

- `E:\agent_misc\subagent_lab\docs\engine-salvage-cross-project-tasks-20260329.md`
- `E:\agent_misc\subagent_lab\docs\mailbox-dev-collaboration-20260329.md`

## Suggested Native Subagent Prompt

```text
Use the repo's main-agent routing workflow on the Salvage Run workload.
If the task needs code changes, choose the right worker tier, then use `reviewer`.
Keep the round small and evidence-backed.
```
