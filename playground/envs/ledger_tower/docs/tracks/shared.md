---
id: playground.ledger_tower.tracks.shared
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
  SOFT_STOP_TICK: string
  SOFT_STOP_PROFILE: string
  SOFT_STOP_GUIDANCE: string
  BUDGET_PROFILE: string
  REPORT_PATH: string
  REFERENCE_POLICY: string
  OFFLINE_PRACTICE_POLICY: string
  PRACTICE_MODE: string
  OFFICIAL_ATTEMPTS: int
  OFFICIAL_SCORING_POLICY: string
  OFFICIAL_ATTEMPT_POLICY: string
  DIRECT_SDK_CLASS: string
  SERVER_SDK_CLASS: string
  HELPER_TIMEOUT_SECONDS: int
---
You are playtesting Ledger Tower in `{{WORKSPACE}}`.

Use only this runner-provided workspace. Do not access or modify the parent
source workspace. Your current working directory is already `{{WORKSPACE}}`.
Use relative paths such as `docs\agent-brief.md`; do not use parent-source
paths.

Runner client: `{{RUNNER_CLIENT}}`
Runner model: `{{MODEL}}`
Runner reasoning variant: `{{REASONING_VARIANT}}`
Runner official move budget: `{{TICK_BUDGET}}`
Runner track budget profile: `{{BUDGET_PROFILE}}`
Runner soft-stop policy: `{{SOFT_STOP_PROFILE}}`

The runner has already provided the official server URL and token through the
process environment. The SDK reads those values automatically; do not inspect,
print, copy, assign, or manually set environment variables in your scripts.
Recommended official submission path: write the final route commands, one per
line, to `logs\route.txt`, then run:

```powershell
python tools\ledger_submit_route.py --route logs\route.txt
```

The helper validates that the route contains only movement/buy commands, creates
one official tracked game, executes the route, calls `verify()`, and writes the
required report. Commands that do not spend a move are recorded and reflected in
route-quality summaries; the helper continues replay by default and stops only
after too many consecutive non-moving commands. Use this helper when you have
selected a route and are ready to spend an official attempt.

If you need direct SDK control instead, create the official tracked game with:

```python
from sdk import {{SERVER_SDK_CLASS}}

{{SERVER_SDK_CLASS}}(new=True, label="{{LABEL}}")
```

Call `new=True` once per official attempt. In later helper scripts for the same
attempt, reconnect with `{{SERVER_SDK_CLASS}}()` when there is only one
token-owned game, or pass the saved `game_id` for the attempt you want to resume.
Calling `verify()` submits that official game and closes it to further commands.
For another scored sample after any verification result, create a fresh official
game with `new=True` if the token still has attempts remaining.
Official attempt count is based on official game creation, not on currently open
games. Verifying or closing a game never refunds, frees, or restores an official
attempt.

Hard rules:

- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- Do not read or glob implementation/data files: `game.py`, `server.py`,
  `mcp_server.py`, `sdk\*.py`, or `data\*.json`.
- Do not read or run route/helper scripts under `scripts\*.txt` unless the
  track reference policy explicitly allows one.
- Track reference policy:
{{REFERENCE_POLICY}}
- Do not invoke the command-line game engine directly. Use only the practice
  mechanism described below; for official play, use `{{SERVER_SDK_CLASS}}`.
- Do not try to start the replay server from this workspace. The runner already
  owns the server process and the SDK has the connection details.
- If you write a temporary Python helper under `logs\`, insert `{{WORKSPACE}}`
  into `sys.path` before importing `sdk`.
- Exploratory Python helpers must be bounded and should finish within
  `{{HELPER_TIMEOUT_SECONDS}}` seconds per script run. Do not run unbounded
  exhaustive search; if a helper times out or grows too broad, switch to a
  simpler heuristic route and submit the best verified route you have.
- Official attempts: `{{OFFICIAL_ATTEMPTS}}`; official scoring policy:
  `{{OFFICIAL_SCORING_POLICY}}`.
- {{OFFICIAL_ATTEMPT_POLICY}}
- Practice mode: `{{PRACTICE_MODE}}`.
  {{OFFLINE_PRACTICE_POLICY}}
- `tower.list_available(kind)` returns one newline-delimited string. Print it
  directly or call `.splitlines()`; do not iterate the string as if it were a
  list.
- Treat `observation["moves"]` as the official hard budget.
- {{SOFT_STOP_GUIDANCE}}
- Do not continue official play beyond move `{{TICK_BUDGET}}`.
- Do not continue an official game after calling `verify()`; that submission is
  final for the game.
- Do not expect `verify()` to free another official attempt. Each `new=True`
  official game consumes one attempt permanently, even if the game later fails
  or is submitted as partial.
- Do not print, dump, echo, log, manually set, or store the raw auth token
  anywhere.

Shared reporting requirements:

- Write the final report to `{{REPORT_PATH}}`.
- Include model, runner, and track.
- Include official game id and verification result if available.
- Include `accepted`, `outcome`, `goalAchieved`, and failed goal keys from
  `goalCompletion.failed`.
- Include final state: moves, floor, HP, attack, defense, gold, keys, inventory,
  and victory.
- Include `softStopTick`, `softStopScoring`, `softStopExceeded`,
  `softStopScore`, and whether the soft stop was enabled or disabled.
- Include key commands or strategy.
- Include failed actions or confusing moments.
- Include feedback on fight preview clarity, map readability, SDK ergonomics,
  and budget clarity.

The track-scoped section below defines this run's goal, disclosure level,
verification call, and any extra report fields.
