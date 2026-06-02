---
id: playground.arcane_lab.deepseek.prestige
engine: mini-mustache
inputs:
  WORKSPACE: string
  MODEL: string
  EFFORT: string
  SAFE_MODEL: string
  TIMESTAMP: string
  LABEL: string
---
You are playtesting Arcane Lab in `{{WORKSPACE}}`.

Use only this runner-provided workspace. Do not access or modify the parent source workspace.

Goal: use player-visible interfaces to discover and complete, or get as close as possible to, the prestige Echo Vault route.

Hard rules:

- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- Do not read `data\arcane_lab.json`.
- Do not use `list goals debug` or `goals_debug`.
- Do not run these scripts as route answers: `scripts\prestige_smoke.txt`, `scripts\late_playtest.txt`, `scripts\retire_smoke.txt`.
- You may read `docs\agent-brief.md`, `docs\sdk-api.md`, and `docs\tasks.md`.
- Prefer SDK or CLI observation commands: `status`, `list goals`, `list spells`, `list recipes`, `list areas`, and normal game commands.
- If you write a temporary Python helper under `logs\`, insert `{{WORKSPACE}}` into `sys.path` before importing `sdk`.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

At the end, write a report to `logs\deepseek_playtest_{{SAFE_MODEL}}_{{TIMESTAMP}}_report.md` containing:

- model/effort if known
- key commands or strategy
- final state
- whether `echo_vault_attuned` and `echo_anchor` were achieved
- any failed actions or confusing moments
- feedback on gradual disclosure and retire decision hints

Then print the report path and a concise result summary.
