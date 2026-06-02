# Game Environments

Each directory under `envs/` is one playable benchmark environment.

Environment directories should own their game engine, data, player-facing docs,
SDK implementation, MCP/server adapters, helper tools, track prompts, and local
smoke command scripts. Shared orchestration stays one level up in
`playground/scripts/`.

New environments should satisfy `../doc/game-environment-contract.md`.

Current environments:

- `arcane_lab/`: magic research text RPG / incremental benchmark.
- `ledger_tower/`: deterministic fixed-value tower puzzle RPG benchmark.
