# Web Port Large Task Round 2026-03-20

## Intent

Use the Round 1 through Round 21 routing probe as enough evidence that this workload family is conservative by default.

For the next experiment batch, stop treating "will the main agent choose to delegate" as the main open question.
Instead, hand the model a deliberately heavy set of large delivery tasks and compare completion quality, validation, time, and token cost.

Record subagent usage, but only as secondary metadata.

## Recommended Use

- Run these tasks on seeded disposable web-port workspaces, not on the current console-only template workspace.
- Keep the Python simulation as the source of truth for rules, scoring, and command resolution.
- Keep validation fixed within a matched comparison.
- Treat each task below as a standalone `large` benchmark task unless you explicitly want a one-shot stress prompt.

## Large Task Batch

### `large_web_port_vertical_slice`

Title:
- First browser-playable vertical slice

Prompt:

```text
Deliver the first browser-playable web port of Salvage Run.

Keep the Python simulation as the source of truth for gameplay rules and command resolution.
Add a local web-serving layer, a serializable snapshot contract, browser rendering for the board/HUD/event log, and a command submission loop with keyboard plus button controls.
Update tests and docs so the web shell can be validated from the CLI.
```

Acceptance:

- Do not duplicate gameplay rules in browser-side JavaScript.
- Keep console mode working.
- Keep the snapshot and command contract deterministic and testable.
- Add or update focused tests for snapshot shape, server command handling, and browser-facing rendering output.

Suggested focus paths:

- `game_engine/`
- `salvage_run/`
- `salvage_run_web/`
- `web/`
- `test/`
- `docs/salvage-run-web-port-workload.md`

Suggested validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- `node --check web/app.js`

### `large_web_port_replay_parity_workbench`

Title:
- Replay viewer and parity workbench

Prompt:

```text
Extend the Salvage Run web port with deterministic replay support.

Reuse the existing script format, add replay loading plus step/autoplay controls in the browser, and surface enough replay metadata to compare console and web final states cleanly.
Keep parity checks scriptable from the CLI.
Update tests and docs.
```

Acceptance:

- Reuse the existing script input format instead of inventing a new replay format.
- Keep console versus web final-state comparisons deterministic for the same seed and scripted inputs.
- Add targeted replay-oriented tests instead of relying on manual browser inspection.
- Keep the browser UI driven by server-owned replay metadata where practical.

Suggested focus paths:

- `game_engine/`
- `salvage_run/`
- `salvage_run_web/`
- `web/`
- `test/`
- `docs/salvage-run-web-port-workload.md`

Suggested validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- `node test/test_web_app_replay_filters.js`
- `node test/test_web_replay_shell_markup.js`

### `large_web_port_operator_polish`

Title:
- Operator HUD, inspection, and terminal-summary polish

Prompt:

```text
Add a substantial interaction-polish pass to the Salvage Run web port without changing gameplay rules.

Implement richer server-owned control/help metadata, selected-tile or selected-entity inspection, clearer hazard/chase/salvage visualization, and a concise end-of-run summary surface that works across active play and replay views.
Update tests and docs.
```

Acceptance:

- Do not change movement, scoring, chase logic, or win/loss rules.
- Prefer server-owned metadata over browser-inferred gameplay status.
- Cover both active-play and terminal/replay states in tests.
- Keep the new surfaces concise enough to remain readable in snapshots and scripted checks.

Suggested focus paths:

- `game_engine/`
- `salvage_run/`
- `salvage_run_web/`
- `web/`
- `test/`
- `docs/salvage-run-web-port-workload.md`

Suggested validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- `node test/test_web_replay_overview_metrics.js`
- `node test/test_web_replay_overview_markup.js`

## Batch Rules

- Keep the three tasks separate so each run still produces a meaningful per-task readout.
- Seed each task from the right milestone baseline instead of forcing every run to start from the same console-only snapshot.
- Do not add reviewer hints or reasoning-effort probes to the prompt unless that is the explicit independent variable of a later experiment.
- If subagents appear, record the topology, but do not treat that as the headline result for this round.

## What This Batch Answers

- whether large web-port delivery tasks change the time/token tradeoff between `single_xhigh` and `subagents`
- whether judged quality diverges once the workload is genuinely end-to-end and UI-heavy
- whether the earlier console-only `large` bucket was simply too small and too local to represent the next benchmark regime
