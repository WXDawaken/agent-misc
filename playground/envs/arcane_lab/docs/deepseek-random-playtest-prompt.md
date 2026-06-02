---
id: playground.arcane_lab.deepseek.random
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

This run is specifically about the `random` crit mode. The runner has already
provided the official server URL and token through the process environment. The
SDK reads those values automatically; do not inspect, print, copy, assign, or
manually set environment variables in your scripts. Create the official tracked
game with `ArcaneLabServerSDK(new=True, label="{{LABEL}}")`.

Goal: use player-visible interfaces to discover and complete, or get as close as
possible to, the prestige Echo Vault route while playing in random crit mode.

Hard rules:

- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- Do not read `data\arcane_lab.json`.
- Do not use `list goals debug` or `goals_debug`.
- Do not run these scripts as route answers: `scripts\prestige_smoke.txt`, `scripts\late_playtest.txt`, `scripts\retire_smoke.txt`.
- You may read `docs\agent-brief.md`, `docs\sdk-api.md`, `docs\tasks.md`, `README.md`, and non-route smoke scripts for API examples.
- Prefer SDK or CLI observation commands: `status`, `list goals`, `list spells`, `list recipes`, `list areas`, `list crit`, and normal game commands.
- If you write a temporary Python helper under `logs\`, insert `{{WORKSPACE}}` into `sys.path` before importing `sdk`.
- The official server token permits only one new server game. Use direct SDK practice games if needed, then spend the official server game carefully.
- Do not call `os.environ[...]`, `os.getenv(...)`, shell `echo`, `set`, `Get-ChildItem Env:`, or similar environment-dump commands for `ARCANE_LAB_*`; let `ArcaneLabServerSDK` read the runner-provided environment internally.
- Do not print, dump, echo, log, manually set, or store the raw auth token anywhere.

Random crit expectations:

- Official play should be through the server-backed SDK so every command, roll,
  and observation lands in `trajectory.json`.
- Random crit rolls are server/state seeded and visible after each `explore` in
  `observation["crit"]["last"]`.
- Use `list crit` or `observation["crit"]` for the current effective crit chance
  and attack bonus; buffs and equipment may change those values.
- You may adapt after observing rolls, but avoid strategies that rely on
  repeatedly creating official games.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

At the end, call server-side `verify()` on the official game with this goal if
you used the server-backed SDK:

```python
{
    "storyline": "echo_vault_attuned",
    "recipe": "echo_anchor",
    "area": "echo_vault",
    "area_clears": 1,
    "retirements": 1,
    "insight": 12,
    "run": 2
}
```

Then write a report to
`logs\deepseek_random_playtest_{{SAFE_MODEL}}_{{TIMESTAMP}}_report.md`
containing:

- model/effort if known
- whether the official attempt used server random crit mode
- official game id and verification result if available
- key commands or strategy
- final state
- whether `echo_vault_attuned` and `echo_anchor` were achieved
- notable random crit rolls that changed decisions
- any failed actions or confusing moments
- feedback on random crit mode, server SDK, gradual disclosure, and retire hints

Then print the report path and a concise result summary.
