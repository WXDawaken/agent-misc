# Playground Game Environment Contract

Last updated: `2026-05-19`

This contract extracts the reusable benchmark requirements from
`doc/mimic-reference-draft.md`. It is the baseline for adding game environments
beside `envs/arcane_lab`.

The goal is not to make every game identical. The goal is to make every game
playable, replayable, scoreable, and comparable through one harness shape.

## Scope

Each environment must be an original, local, text/SDK-playable benchmark game.
It may mimic public genre-level mechanics, but it must not copy commercial game
names, maps, prose, art, exact numeric tables, puzzle layouts, unique story
beats, or spoiler-heavy progression.

Every environment must support:

- deterministic or server-seeded play
- text commands or structured SDK calls
- persisted trajectories
- server-side official verification
- player-facing docs
- isolated agent workspace packaging
- track-specific disclosure and scoring policy

## Source Layout

Required layout:

```text
playground/
  envs/
    <env_id>/
      README.md
      game.py
      data/
      sdk/
      docs/
        agent-brief.md
        sdk-api.md
        tasks.md
        tracks/
          config.json
          shared.md
      scripts/
      tools/
```

Allowed variations:

- `data/` may be empty for code-only puzzle generators, but generation must be
  deterministic from explicit seeds.
- `tools/` is optional unless a track ships a helper.
- Extra docs are fine, but track reference policy must decide what an agent may
  read.

Root-level compatibility shims may point to the default environment, but new
shared runner code should resolve an explicit `env_id`.

## Environment Adapter

Each environment should expose an adapter that can be called by the unified
server. The adapter boundary is deliberately small:

```python
class EnvironmentAdapter:
    env_id: str
    display_name: str

    def new_state(self, *, seed: str | None = None, options: dict | None = None) -> dict: ...
    def observe(self, state: dict, *, include_text: bool = True) -> dict: ...
    def step(self, state: dict, command: str) -> tuple[dict, dict]: ...
    def score(self, state: dict, goal: dict | None = None, policy: dict | None = None) -> dict: ...
    def verify(self, state: dict, trajectory: dict, policy: dict) -> dict: ...
```

`step` returns the updated state plus a result object with:

- `command`: original command string
- `ok`: boolean command acceptance
- `done`: whether the game session ended
- `output`: player-facing text
- `observation`: structured post-command observation
- `events`: optional list of semantic events
- `cost`: optional per-command cost such as turns, ticks, mistakes, calls, or
  budget units

The adapter owns game mechanics. The unified server owns auth, persistence,
trajectory shape, official attempt limits, and HTTP/MCP framing.

## Observation Contract

Observations must be JSON-serializable and stable enough for agents to use
programmatically. Each observation should include:

- `env_id`
- `game_id` when server-backed
- `done`
- a primary progress metric, such as `turn`, `tick`, or `step`
- a `budget` object when a track has an official budget
- environment-specific `state` fields
- `available_commands` or discoverable `list` commands
- optional `status_text` for human-readable summaries

Recommended budget shape:

```json
{
  "budget": {
    "metric": "lifetime_tick",
    "used": 123,
    "limit": 260,
    "soft_stop": 240,
    "exceeded": false,
    "soft_stop_exceeded": false
  }
}
```

The metric name is environment-defined. Arcane Lab uses `lifetime_tick`; a tower
game might use `moves`; a deduction game might use `claims` or `inspections`.

## Command Contract

Official play is command-driven. Commands may be plain text or serialized
structured commands, but the replay trajectory must preserve the exact input.

Each environment must define:

- zero-cost inspection commands, such as `status`, `observe`, `list`, or
  `preview`
- budget-spending action commands
- invalid command behavior
- whether same-command batching is allowed
- how command priority is resolved when batching is allowed

Invalid commands should not crash the game. They should produce `ok=false` and
a useful error message. Whether invalid commands spend budget is an environment
policy and must be documented per track if it matters.

## Server Contract

The local server entrypoint is `playground/server.py`. It must dispatch to a
specific environment by `--env <env_id>` while preserving the default
environment for older commands. Environment-specific replay/static assets should
live under the environment directory, for example
`envs/<env_id>/static/replay.html`, not embedded in Python server code.

Shared HTTP/auth/replay framing, token registry base, persisted session
storage, trajectory writing, budget-policy verification, and the adapter
protocol belong in `playground/server_core.py`. Environment server modules
should provide an `EnvironmentServerSpec`, environment adapter, token-policy
extensions, budget metric policy, and static asset loader.

The unified server should provide the same external HTTP shape for all
environments:

- `POST /api/games` creates a server-backed game.
- `GET /api/games/{game_id}` returns summary plus current observation.
- `GET /api/games/{game_id}/state` returns current structured observation.
- `POST /api/games/{game_id}/command` executes one command.
- `POST /api/games/{game_id}/commands` executes a batch of commands in order.
- `POST /api/games/{game_id}/score` scores without finalizing.
- `POST /api/games/{game_id}/verify` submits an official attempt and writes
  official verification.
- `GET /api/games/{game_id}/trajectory` returns the persisted trajectory.
- `GET /api/auth/status` returns token policy and remaining official attempts.

Server-side token policy is authoritative for:

- `env_id`
- `track`
- max new games
- official budget metric and limit
- soft stop, when enabled
- soft-stop scoring policy, when enabled
- seed or seed hash
- goal policy
- allowed stochastic mode, if any

Agents should not need to inspect or manually set auth environment variables.
Server SDKs must read runner-provided connection details automatically.

## Trajectory Contract

Every server-backed game must persist:

```text
logs/server/games/<game_id>/
  state.json
  trajectory.json
  verification.json   # after official verify/submission
```

Trajectory entries must include:

- monotonically increasing entry index
- timestamp
- command
- result status
- player-facing output
- pre/post primary progress metric when useful
- post-command observation
- semantic events
- random or stochastic roll metadata when visible to the player

The trajectory hash should be computed from stable session metadata and entries,
not from filesystem paths or timestamps alone.

## Verification Contract

`verify` must be server-side for official attempts. A verification result must
include:

- `accepted`: whether server policy accepted the attempt
- `outcome`: `success`, `partial`, `accepted`, or `rejected`
- `reward`: numeric score
- `goal_achieved`: boolean or null
- `goal_completion`: achieved count, total count, failed keys
- `budget`: metric, used, limit, exceeded, soft-stop status
- `trajectory_hash`
- environment-specific metrics

Success means the track goal was achieved and the hard policy passed. Partial
means the server accepted the attempt but some goals are missing. Rejected means
a hard policy failed, such as budget overrun or invalid token use.

Soft stop is optional. When present, it is advisory and must not zero reward by
itself. Tracks may disable it with `soft_stop: false` when the hard budget and
environment score already carry the intended route-quality signal. Enabled
tracks may choose one of these `soft_stop_scoring` policies:

- `binary` default: `softStopScore` is `1` when the soft stop is respected and
  `0` after the first overrun.
- `linear_to_hard_budget`: `softStopScore` is `1` at or before the soft stop and
  linearly decays to `0` at the hard budget. This policy requires a hard budget;
  if the hard budget is equal to or below the soft stop, the first overrun reaches
  `0`.

Verification results should include `softStopTick`, `softStopScoring`,
`softStopScore`, `softStopOverrun`, and the same policy/score inside
`compliance.softStop`. For disabled soft stops, `softStopTick` and
`softStopScore` should be null and route/run quality should not apply a
soft-stop penalty. Runner route/run quality may use `softStopScore`, but the
official reward remains the environment score plus explicit goal bonuses unless
the hard budget fails.

`verify` is a submission boundary for official games. After the first successful
`POST /verify`, the server must treat that game as submitted/finalized and reject
further mutating commands on it. Repeated verification may return the saved
submission result, but must not allow agents to repair the same official game
after seeing a partial or rejected result. When more official attempts remain,
the agent must create a fresh official game.

When a track grants more than one official attempt for the same task id, the
runner-level score is best-of-N across independent verified official games.
Select the verification with the highest reward, then use accepted outcome and
environment-specific route quality as tie breakers. Practice-token games are
non-official and must not be verifiable.

Official-attempt limits count official game creations, not active open games.
Creating a new official game consumes one official attempt permanently.
Verification submits/finalizes that game but never refunds, frees, or restores
the consumed attempt, even when the submitted result is partial or rejected.

## Track Contract

Each environment owns `docs/tracks/config.json`. Tracks should declare:

- `prompt_path`
- `shared_prompt_path` or environment default
- `offline_practice`
- `practice.mode`: `whitebox`, `server-token`, or `none`
- `official_attempts` or `official.max_new_games`
- `official_scoring`: `single` or `best_of_n`
- `goal`
- `budget_metric`
- hard budget limit
- soft stop, when enabled
- soft-stop scoring policy, when different from the shared `binary` default
- stochastic/seed policy
- variant data path, when a track intentionally changes map or rules data
- reference policy
- source-policy forbidden patterns
- provided helper paths, if any
- helper-script runtime guidance or caps when tracks permit agents to write
  exploratory scripts
- suite membership

Tracks should be capability-shaped, not just difficulty-shaped. Good examples
from the mimic draft:

- long-horizon incremental routing
- exact finite-resource spatial optimization
- tactical grid state under partial observability
- evidence synthesis and structured deduction
- constructive logistics and throughput design
- stochastic build robustness
- protocol/manual following

## Workspace Packaging Contract

Agent workspaces must be generated, not hand-maintained. The setup script should
copy only the files allowed by the selected track.

Two official workspace modes are required:

- `direct-sdk`: includes local engine/data/SDK for offline practice plus the
  server SDK for official play.
- `server-only`: includes only player-facing docs and server-backed SDK files.

Both modes must omit by default:

- historical logs
- saves
- prior agent workspaces
- server source
- route-answer scripts
- hidden data/source when a track is testing discovery

Flattened workspaces are allowed even when source environments live under
`envs/<env_id>`, because stable agent-facing paths reduce prompt churn.

## Replay UI Contract

The replay UI should have a common shell and environment-specific panels.

Common display:

- game id, env id, track, model/run metadata
- command timeline
- budget line and soft-stop line
- verify outcome and goal completion
- failed command markers
- stochastic event markers
- trajectory hash

Environment-specific display:

- Arcane Lab: resources, storylines, crit rolls, retire markers
- Ledger Tower: map position, hp, keys, damage previews, door/shop choices
- Grid Relic: units, hazards, enemy intents, line of sight
- Caseboard: evidence graph, claims, contradictions
- Foundry Lines: layout, throughput, congestion, simulation ticks

## SDK/MCP Contract

Each environment should provide:

- direct SDK for offline practice when allowed
- server SDK for official play
- MCP tools/resources when useful
- docs that match the SDK surface

Minimum SDK surface:

```python
lab = EnvSDK(new=True)
lab.step("command")
lab.run(["command 1", "command 2"])
lab.observe()
lab.score(goal)
lab.export_tracking(path)

official = EnvServerSDK(new=True)
official.step("command")
official.verify()
official.trajectory()
official.auth_status()
```

Environment-specific SDK names are fine, but shared runners should prefer a
generic server SDK wrapper once multiple environments exist.

## Candidate Fit Checklist

Before implementing a new environment from `mimic-reference-draft.md`, answer:

- What capability axis does it add beyond Arcane Lab?
- What is the smallest deterministic version?
- What is the primary budget metric?
- What does `observe` expose?
- What information is hidden by player-facing rules?
- What does an official trajectory look like?
- What are the first three tracks?
- What is the reference success route or solution?
- Which files are allowed in direct practice and server-only modes?
- What makes a run `success`, `partial`, or `rejected`?

`Ledger Tower` currently satisfies this checklist best for the next environment:
finite deterministic state, exact arithmetic, compact replay, obvious scoring,
and a capability axis that differs cleanly from Arcane Lab.
