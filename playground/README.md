# Playground

Purpose: host lightweight game environments for testing broad agent capability.

The active environments are `Arcane Lab`, a local text RPG / incremental
benchmark, and `Ledger Tower`, a deterministic fixed-value tower puzzle RPG.
Future games should be added as sibling directories under `envs/`.

## Layout

- `envs/arcane_lab/`: Arcane Lab game engine, data, SDK, MCP adapter, replay
  server, player docs, track prompts, helper tools, and deterministic smoke
  command scripts.
- `envs/ledger_tower/`: Ledger Tower game engine, data, SDK, MCP adapter,
  replay server, player docs, track prompts, and deterministic smoke command
  scripts.
- `server_core.py`: shared HTTP/auth/replay server core, token registry base,
  persisted session store, budget-policy verifier, and adapter protocol used
  by environment server specs.
- `doc/`: shared design notes and contracts for adding more environments.
- `scripts/`: shared operator harnesses, verifier entrypoints, runner setup, and
  model-launch wrappers.
- `agent_workspaces/`: generated isolated workspaces for agent playtests.
- `logs/`: replay server games, verification files, screenshots, and run logs.
- `saves/`: local save files.
- `scripts/atif_export.py`: export runner summaries or server game trajectories
  to Harbor ATIF `trajectory.json` shape.
- root `server.py`: unified local server entrypoint. It defaults to
  `arcane_lab` and accepts `--env <environment_id>` before server arguments or
  subcommands.
- root `game.py`, `mcp_server.py`, and `sdk/`: compatibility shims that point
  to the current default environment, `arcane_lab`.

Agent workspaces are still flattened intentionally: a track that permits offline
practice receives files such as `game.py`, `data/`, and `sdk/` at the workspace
root so existing prompts and SDK examples remain stable.

The shared environment contract is in
`doc/game-environment-contract.md`. Use it before adding another game.

## ATIF Export

Runner summaries automatically include `.runner/atif_trajectory.json` when a
run has enough metadata to build one. You can also export historical artifacts:

```powershell
python scripts\atif_export.py --summary agent_workspaces\reasonix_runs\<RUN>\.runner\summary.json --validate
python scripts\atif_export.py --game-id <GAME_ID> --validate
python scripts\atif_export.py --trajectory logs\server\games\<GAME_ID>\trajectory.json --validate
```

The exporter keeps the native `verification.json` and replay `trajectory.json`
unchanged, then writes ATIF with the task prompt, game command tool calls,
environment observations, final report, and playground reward/route metadata.

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
unless you have added deployment-grade authentication and isolation.

## Arcane Lab

Use the environment README for game-specific details:

- `envs/arcane_lab/README.md`
- `envs/arcane_lab/docs/agent-brief.md`
- `envs/arcane_lab/docs/sdk-api.md`
- `envs/arcane_lab/docs/tasks.md`
- `envs/arcane_lab/docs/tracks/README.md`

The root entrypoints keep existing commands working:

```powershell
python game.py --new --script scripts/smoke.txt --no-save
python scripts/verify.py --new --script scripts/smoke.txt --goal-storyline field_notes
python server.py --host 127.0.0.1 --port 8765 --require-token
python server.py --env arcane_lab --host 127.0.0.1 --port 8765 --require-token
python server.py mint-token --task-id local-smoke --max-new-games 1
```

Agent code should use SDK entrypoints rather than command-line route scripts:

```python
from sdk import ArcaneLabSDK, ArcaneLabServerSDK

practice = ArcaneLabSDK(new=True)
official = ArcaneLabServerSDK(new=True)
```

## Ledger Tower

Use the environment README for game-specific details:

- `envs/ledger_tower/README.md`
- `envs/ledger_tower/docs/agent-brief.md`
- `envs/ledger_tower/docs/sdk-api.md`
- `envs/ledger_tower/docs/tasks.md`

Run local smoke routes:

```powershell
python envs\ledger_tower\game.py --new --script scripts\ledger_clear_smoke.txt --no-save
python server.py --env ledger_tower --host 127.0.0.1 --port 8765 --require-token
python server.py --env ledger_tower mint-token --task-id local-ledger --max-new-games 1
```

Inside a Ledger Tower agent workspace, agent code should use the Ledger SDK
entrypoints:

```python
from sdk import LedgerTowerSDK, LedgerTowerServerSDK

practice = LedgerTowerSDK(new=True)
official = LedgerTowerServerSDK(new=True)
```
