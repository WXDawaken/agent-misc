# Arcane Lab SDK and MCP

Arcane Lab follows the useful shape of [RuneBench](https://github.com/MaxBittker/RuneBench) at a smaller scale:

- agents play through a compact SDK instead of natural-language-only turns
- MCP exposes the same SDK as tools
- markdown resources give the agent strategy and API context
- a verifier writes `reward.json`, `reward.txt`, and tracking data

## Server-Backed Python SDK

For agent playtests, prefer the server-backed SDK so every command is recorded
in the replay trajectory. Benchmark runners start the replay server and provide
connection/authentication through environment variables; agent code should let
the SDK read those values automatically.

```python
from sdk import ArcaneLabServerSDK

lab = ArcaneLabServerSDK(new=True, label="agent-run")
print(lab.observe()["status_text"])

result = lab.step("study ember 3")
print(result.output)

for result in lab.run([
    "study stone 3",
    "cast shape_pebble",
    "tick 2",
    "batch cast stone_skin@1 fire_lance@2",
    "explore training_yard 2",
]):
    print(result.command, result.reward)

print(lab.game_id)
print(lab.trajectory()["entries"][-1]["command"])
```

`ArcaneLabServerSDK` lives in a server-only module and can be imported from a
lean runner workspace. The local practice backend is loaded only when
`ArcaneLabSDK` is explicitly used.

The server writes each game to `logs/server/games/<game_id>/state.json` and
`logs/server/games/<game_id>/trajectory.json`.

For official benchmark attempts, the runner mints a token before handing the
workspace to an agent. The SDK reads the provided values automatically; agent
code should not inspect, print, copy, assign, or manually set them. Then use:

```python
from sdk import ArcaneLabServerSDK

lab = ArcaneLabServerSDK(new=True, label="official-run")
lab.step("study ember 3")
result = lab.verify({"storyline": "field_notes"}, tick_budget=25)
print(result["trajectory_hash"])
```

Official verification is server-side only. It writes
`logs/server/games/<game_id>/verification.json` and includes a
`trajectory_hash` over the recorded trajectory. If the token has a
`tick_budget`, that server-side lifetime budget is authoritative: any request-side
`tick_budget` is recorded in `policy` but cannot override the token budget.
If the token has a `soft_stop_tick`, verification scores it separately as
`softStopScore` without changing hard-budget acceptance.
Use `per_run_tick_budget` only when a task intentionally constrains the current
run tick separately from lifetime ticks.
Token goals also win over request goals for matching keys, while request goals
may add extra non-conflicting checks. Direct SDK games are useful for practice,
but they are not official verified runs. Current official tracks set
`offline_practice: true` and include offline support for
`ArcaneLabSDK` practice, then require `ArcaneLabServerSDK` for the one official
server-tracked attempt. Future tracks can disable offline practice and ship only
the server-backed SDK.

Official tasks can select crit rules at token mint time:

`charge` is the default deterministic mode: successful non-critical explores add
focus charge, and a full charge makes the next explore gain an attack bonus.
`random` uses a server-side seed and records each roll in the replay trajectory.
`status`, `list crit`, and `observe()["crit"]` expose current effective crit
values after buffs and equipment. `auth_status()` exposes the crit mode and seed
hash, not the raw seed.

## Direct Python SDK

The direct SDK exists for offline practice and verifier internals. It does not
send commands to the replay server, so direct games are not official attempts.

```python
from sdk import ArcaneLabSDK

lab = ArcaneLabSDK(new=True)
print(lab.observe()["status_text"])

result = lab.step("study ember 3")
print(result.output)

for result in lab.run([
    "study stone 3",
    "cast shape_pebble",
    "tick 2",
    "batch cast stone_skin@1 fire_lance@2",
    "explore training_yard 2",
]):
    print(result.command, result.reward)

lab.export_tracking("logs/my_run_tracking.json")
```

For stochastic practice, pass a local seed:

```python
lab = ArcaneLabSDK(new=True, crit_mode="random", crit_seed="practice-seed")
```

Important methods:

- `observe()`: structured state plus `status_text`; includes current-run `tick`, persistent `lifetime_tick`, `assignments`, active `buffs`, `crit`, `last_action`, `action_costs`, visible `next_goals`, equipment enhancement/spare state, area requirements/boss soft counters, and `hidden_goal_count`
- `step(command)`: run one command and return output, observation, reward, and done flag
- `run(commands)`: run a short command list
- `list_available(kind)`: returns a newline-delimited string for `spells`, `recipes`, `areas`, `goals`, `goals_debug`, `automation`, `buffs`, `crit`, or `actions`
- `score(goal=None)`: verifier-style reward metrics
- `trajectory()`: server-backed SDK only; fetch full replay trajectory
- `verify(goal=None, tick_budget=None, lifetime_tick_budget=None, soft_stop_tick=None, per_run_tick_budget=None)`: server-backed SDK only; official server-side scoring
- `auth_status()`: server-backed SDK only; inspect token limits
- `save(path=None)`: direct SDK writes state JSON; server-backed SDK autosaves on the server
- `export_tracking(path)`: write samples and transcript

Server-backed methods map to HTTP:

- `ArcaneLabServerSDK(..., new=True)`: `POST /api/games`; if server URL, game id, auth token, crit mode, or crit seed arguments are omitted, the SDK reads the corresponding runner-provided environment values by default
- `observe()`: `GET /api/games/<game_id>/state`
- `step(command)`: `POST /api/games/<game_id>/command`
- `run(commands)`: repeated `step(command)`
- `list_available(kind)`: `GET /api/games/<game_id>/list/<kind>`
- `score(goal=None)`: local cached score for no goal, or `POST /api/games/<game_id>/score`
- `trajectory()`: `GET /api/games/<game_id>/trajectory`
- `verify(goal=None, tick_budget=None, lifetime_tick_budget=None, soft_stop_tick=None, per_run_tick_budget=None)`: `POST /api/games/<game_id>/verify`

SDK result shapes:

```python
obs = lab.observe()
print(obs["elements"]["ember"]["level"])
print(obs["elements"]["ember"]["xp"])
print(obs["areas"]["training_yard"]["progress"])
print(obs["areas"]["training_yard"]["clears"])
print(obs["areas"]["training_yard"]["requires_attack"])
print(obs["areas"]["training_yard"]["boss"])
print(obs["equipment_levels"])
print(obs["equipment_spares"])

# list_available returns text, not a list of lines.
print(lab.list_available("areas"))
for line in lab.list_available("areas").splitlines():
    print(line)
```

Batch commands:

- `batch cast fire_lance stone_skin`: spend one cast tick and try both spells in order
- `batch cast stone_skin@1 fire_lance@2`: explicit priority, lower number first
- `batch transmute focus_lens guard_charm`: spend one transmute tick and try both recipes in order
- Duplicate payload ids in one batch are rejected.
- `enhance focus_lens`: instantly consume spare +0 copies and raise the recipe stack by one enhancement level. Effects use `1.1 ** level`; the next levels cost 1, 2, 4, 8, 16 spare +0 copies by default, capped at +5 unless a recipe overrides it.

Storyline visibility:

- `observe()["next_goals"]` returns visible storyline goals with progress entries, not raw condition dictionaries.
- `observe()["hidden_goal_count"]` reports how many distant incomplete storylines are still hidden.
- `list_available("goals")` mirrors player-facing gradual disclosure.
- `list_available("goals_debug")` returns all incomplete storyline conditions for verifier authors and balance tuning.

## MCP Server

The MCP server exposes the same game interface for integrations. Benchmark
agents should use whatever MCP configuration the runner supplies instead of
starting MCP processes themselves.

Tools:

- `new_game`
- `observe`
- `execute_command`
- `run_commands`
- `list_available`
- `score`
- `save_game`

Resources:

- `arcane-lab://agent-brief`
- `arcane-lab://design`
- `arcane-lab://sdk-api`

## Verifier

Official agent attempts should use server-side `lab.verify(...)`. Local
operator verifier scripts exist for benchmark authors, but they are not part of
the agent play surface.

Use a lifetime game tick budget instead of a command-count limit.

If lifetime ticks exceed the budget, the verifier keeps the state and tracking output but sets reward to `0` and marks `tickBudgetExceeded`. The current run tick is still reported for route analysis and can be constrained separately with `--per-run-tick-budget`.

Use `--soft-stop-tick` for advisory route discipline. It records
`softStopExceeded`, `softStopOverrun`, and `softStopScore` without zeroing reward.

Verifier and server `verify()` results split hard acceptance from goal
completion. `accepted` means the hard budget/token policy accepted the run;
`goalAchieved`, `goalCompletion`, and `outcome` indicate whether every scored
goal subcheck passed or which goal keys are still missing.

It also writes `summary.txt` next to `reward.json` for a readable reason while keeping `reward.txt` numeric for benchmark compatibility.

Automation-specific, retirement-specific, and area-progress goals are supported
through the same goal dictionary shape used by server-side verification.

Outputs:

- `logs/verifier/reward.json`
- `logs/verifier/reward.txt`
- `logs/verifier/summary.txt`
- `logs/verifier/tracking.json`

The score is intentionally transparent: storylines, area clears, element levels, equipment, enhancement levels, wizards, insight, coins, and resource stock all contribute. Optional goal bonuses make benchmark tasks sharper.
