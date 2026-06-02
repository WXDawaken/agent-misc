---
id: playground.arcane_lab.tracks.shared
engine: mini-mustache
inputs:
  WORKSPACE: string
  RUNNER_CLIENT: string
  MODEL: string
  REASONING_VARIANT: string
  TICK_BUDGET: int
  LABEL: string
  TRACK: string
  SAFE_MODEL: string
  TIMESTAMP: string
  SOFT_STOP_TICK: int
  BUDGET_PROFILE: string
  REPORT_PATH: string
  REFERENCE_POLICY: string
  OFFLINE_PRACTICE_POLICY: string
  CRIT_RULES: string
  CRIT_PRACTICE_KWARGS: string
---
You are playtesting Arcane Lab in `{{WORKSPACE}}`.

Use only this runner-provided workspace. Do not access or modify the parent source workspace.
Your current working directory is already `{{WORKSPACE}}`. Use relative paths
such as `docs\agent-brief.md`; do not use parent-source paths.

Runner client: `{{RUNNER_CLIENT}}`
Runner model: `{{MODEL}}`
Runner reasoning variant: `{{REASONING_VARIANT}}`
Runner official lifetime tick budget: `{{TICK_BUDGET}}`
Runner track budget profile: `{{BUDGET_PROFILE}}`

This run uses server-tracked crit rules. {{CRIT_RULES}} The runner has already provided
the official server URL and token through the process environment. The SDK reads
those values automatically; do not inspect, print, copy, assign, or manually
set environment variables in your scripts. Create the official tracked game with:

```python
from sdk import ArcaneLabServerSDK

ArcaneLabServerSDK(new=True, label="{{LABEL}}")
```

Call `new=True` only for the first official game creation. In later helper
scripts for the same attempt, reconnect with `ArcaneLabServerSDK()` so the SDK
resumes the token-owned game.

Hard rules:

- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- Do not read or glob implementation/data files: `game.py`, `server.py`,
  `mcp_server.py`, `sdk\*.py`, or `data\*.json`.
- Do not use `list goals debug` or `goals_debug`.
- Do not read or run route/helper scripts under `scripts\*.txt` unless the
  track reference policy explicitly allows one.
- Track reference policy:
{{REFERENCE_POLICY}}
- Do not invoke the command-line game engine directly. For offline practice, use
  `ArcaneLabSDK` from a Python helper under `logs\`; for official play, use
  `ArcaneLabServerSDK`. Issue `status`, `list goals`, `list spells`, `list
  recipes`, `list areas`, `list crit`, and normal game commands through the SDK.
- Do not try to start the replay server from this workspace. The runner already
  owns the server process and the SDK has the connection details.
- If you write a temporary Python helper under `logs\`, insert `{{WORKSPACE}}` into `sys.path` before importing `sdk`.
- The official server token permits only one new server game. {{OFFLINE_PRACTICE_POLICY}}
- `lab.list_available(kind)` returns one newline-delimited string. Print it directly or call `.splitlines()`; do not iterate the string as if it were a list.
- `lab.observe()` returns dictionaries: use `obs["elements"]["ember"]["level"]`, `obs["elements"]["ember"]["xp"]`, `obs["areas"]["training_yard"]["progress"]`, and `obs["areas"]["training_yard"]["clears"]`. Equipment enhancement uses `obs["equipment_levels"]` and `obs["equipment_spares"]`. Area entries may include `boss` final-clear pressure mechanics; `list areas` prints the same soft-counter hints in text form.
- Do not call `os.environ[...]`, `os.getenv(...)`, shell `echo`, `set`, `Get-ChildItem Env:`, or similar environment-dump commands for `ARCANE_LAB_*`; let `ArcaneLabServerSDK` read the runner-provided environment internally.
- Treat `observation["lifetime_tick"]` as the official hard budget. `observation["tick"]` is only current-run tick and may reset after retirement.
- Treat lifetime tick `{{SOFT_STOP_TICK}}` as a soft scoring line, not the hard cutoff. Before crossing it, checkpoint carefully and avoid speculative grinding. At or after it, stop exploratory progression by default; only spend additional hard-budget ticks when you can name a short, concrete command sequence that completes a known official goal. If you cross the soft stop, report the tradeoff through `softStopExceeded` / `softStopScore`.
- Do not continue official play beyond lifetime tick `{{TICK_BUDGET}}`.
- Do not print, dump, echo, log, manually set, or store the raw auth token anywhere.

Random crit expectations:

- Official play should be through the server-backed SDK so every command, roll,
  and observation lands in `trajectory.json`.
- For direct offline practice on this random-mode track, create local practice
  games with `ArcaneLabSDK(new=True, {{CRIT_PRACTICE_KWARGS}})` or another fixed
  practice seed so practice matches the official crit rules.
- Random crit rolls are server/state seeded and visible after each `explore` in
  `observation["crit"]["last"]`.
- Use `list crit` or `observation["crit"]` for the current effective crit chance
  and attack bonus; buffs and equipment may change those values.
- You may adapt after observing rolls, but avoid strategies that rely on
  repeatedly creating official games.

Shared reporting requirements:

- Write the final report to `{{REPORT_PATH}}`.
- Include model, runner, and track.
- Include whether the official attempt used server random crit mode.
- Include official game id and verification result if available.
- Include `accepted`, `outcome`, `goalAchieved`, and any failed goal keys from `goalCompletion.failed`.
- Include final state: `lifetime_tick`, current run `tick`, run, reward, completed storylines, insight, and retirements.
- Include `softStopTick`, `softStopExceeded`, `softStopScore`, and whether you obeyed the soft stop.
- Include key commands or strategy.
- Include notable random crit rolls that changed decisions.
- Include failed actions or confusing moments.
- Include feedback on random crit mode, server SDK, gradual disclosure, retire hints, and budget clarity.

The track-scoped section below defines this run's goal, disclosure level,
verification call, and any extra report fields.
