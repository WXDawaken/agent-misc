# Arcane Lab

Purpose: provide a text RPG game environment for testing an agent's broad capabilities.

This is the first environment under the playground's multi-environment layout.
In the source tree, files live in `envs/arcane_lab`; runner-created agent
workspaces flatten the same files to the workspace root for compatibility.
Follow the paths given by the current runner prompt when they differ.

The active prototype is `Arcane Lab`, an original magic research incremental RPG testbed. It is inspired by the broad public feature shape of Magic Research 2: spells, elemental study, transmutation, automation, exploration, storylines, and retirement. It does not copy the original game's text, assets, exact progression, or hidden content.

Manual actions now consume game ticks: `study`, `cast`, `explore`, `transmute`, and `hire` each take 1 tick, while wizard automation can run during those ticks.

Compatible same-verb payloads can be batched, for example `batch cast stone_skin@1 fire_lance@2`, which spends one action tick and resolves payloads by priority.

Benchmark tasks should prefer `--tick-budget` over command-count limits. `--tick-budget` is a lifetime tick budget across retirements; use `--per-run-tick-budget` only when a task intentionally constrains the current run.
Verifier runs keep `reward.txt` numeric and write `summary.txt` for readable budget/goal status.

Prompt tracks under `docs/tracks/` split the same game into different
information regimes: blind discovery, visible goal, budgeted prestige, and route
optimization. OpenCode Go playtests can select one with `-Track`.

Storyline goals are gradually disclosed: `list goals` shows visible current goals and progress hints, while `list goals debug` / `goals_debug` keeps full conditions available for benchmark authors.

Crit rules now have two modes. The default `charge` mode is deterministic:
successful non-critical explores build focus charge, and full charge gives the
next explore +20% attack. `random` mode uses a server/state seed, records every
roll in trajectory observations, and is intended for stochastic benchmark
variants. `status`, `list crit`, and SDK observations report current effective
crit values after buffs and equipment.

## Safety

This project is a local benchmark/game environment, not a security sandbox.
Agents may execute code, write files, inspect allowed workspace contents, and
generate long logs. Run untrusted or third-party agents only in isolated
workspaces with low-privilege credentials.

Do not commit secrets or runtime artifacts. In particular, keep API keys,
server auth tokens, generated agent workspaces, save files, server game logs,
trajectory logs, and provider/tool caches out of published history. Review
`logs/`, `saves/`, `agent_workspaces/`, and any runner output before publishing
or sharing a branch.

The replay/server path is intended for local use. Bind it to `127.0.0.1`, use
attempt tokens for official runs, and avoid exposing it on a public network
unless you have added a real deployment-grade authentication and isolation
layer.

## Run

Agent playtests should use the SDK rather than command-line entrypoints or
bundled route scripts. Offline practice uses the direct SDK:

```python
from sdk import ArcaneLabSDK

lab = ArcaneLabSDK(new=True)
print(lab.step("status").output)
```

The replay server is operator-owned. In official benchmark workspaces the runner
starts it outside the agent workspace and supplies connection/authentication to
the server-backed SDK.

Agent playtests should connect through the server-backed SDK so commands are
recorded automatically:

```python
from sdk import ArcaneLabServerSDK

lab = ArcaneLabServerSDK(new=True, label="agent-run")
lab.step("study ember 3")
print(lab.trajectory()["entries"][-1]["command"])
```

Runner workspaces are track-configurable. Current official tracks include the
direct SDK engine for offline practice plus allowed player-facing docs, but
future tracks can disable offline practice and ship only the server-backed SDK.
Both modes omit historical route artifacts. Official attempts should use the
server-backed SDK.

For official agent attempts, the runner uses a single-use attempt token.
`ArcaneLabServerSDK(new=True)` reads the server URL and auth token automatically
and attaches the token on every request; agents should not manually inspect,
set, print, or store those values. Server-side `verify()` writes
`verification.json` with a `trajectory_hash`; when the token includes
`--tick-budget`, that server lifetime budget is authoritative and request-side
budgets are only recorded in the verification policy. Stochastic official tasks
can mint with `--crit-mode random`; the raw crit seed stays server-side while
auth status exposes only a seed hash.

## Files

- game engine and data files: local content and tuning
- SDK package: Python SDK for agent play
- MCP adapter: exposes game tools/resources for configured integrations
- replay server: local server with per-game command trajectories and web UI
- `docs/design.md`: design notes and grounding
- `docs/agent-brief.md`: instructions for an agent player
- `docs/sdk-api.md`: SDK, MCP, and verifier reference
- `docs/tasks.md`: benchmark task sketches
- `docs/tracks/`: prompt tracks for varying information disclosure
- `scripts/`: deterministic command scripts used by operator smoke tests; most
  agent tracks omit these route scripts
- `saves/`: generated save files
- `logs/`: generated transcripts and notes

## Suggested Test Axes

- long-horizon planning and memory
- inventory and resource bookkeeping
- tool use and file editing
- puzzle solving under partial information
- recovery from ambiguity or failed actions
- narrative consistency and user communication

Keep experiments isolated here unless they become shared benchmark infrastructure.
