You are playtesting Arcane Lab in `{{WORKSPACE}}`.

Use only this runner-provided workspace. Do not access or modify the parent source workspace.
Your current working directory is already `{{WORKSPACE}}`. When reading docs or
scripts, use relative paths such as `docs\agent-brief.md` or absolute paths that
start with `{{WORKSPACE}}`; do not use parent-source paths from
`E:\agent_misc\playground\envs\arcane_lab\...`.
For shell commands, do not `cd` to an absolute path. Run commands from the
current directory, or use relative paths from the current directory.

Runner client: OpenCode Go
Runner model: `{{MODEL}}`
Runner reasoning variant: `{{REASONING_VARIANT}}`
Runner official lifetime tick budget: `{{TICK_BUDGET}}`

This run is specifically about the `random` crit mode. The runner has already
provided the official server URL and token through the process environment. The
SDK reads those values automatically; do not inspect, print, copy, assign, or
manually set environment variables in your scripts. Create the official tracked
game with:

```python
ArcaneLabServerSDK(new=True, label="{{LABEL}}")
```

Goal: use player-visible interfaces to discover and complete, or get as close as
possible to, the prestige Echo Vault route while playing in random crit mode.

Hard rules:

- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- Do not read `data\arcane_lab.json`.
- Do not use `list goals debug` or `goals_debug`.
- Do not run route answer scripts: `scripts\midgame_smoke.txt`, `scripts\late_playtest.txt`, `scripts\retire_smoke.txt`, or `scripts\prestige_smoke.txt`.
- You may read `README.md`, `docs\agent-brief.md`, `docs\sdk-api.md`, `docs\tasks.md`, and `scripts\smoke.txt` for API examples.
- Prefer SDK or CLI observation commands: `status`, `list goals`, `list spells`, `list recipes`, `list areas`, `list crit`, and normal game commands.
- If you write a temporary Python helper under `logs\`, insert `{{WORKSPACE}}` into `sys.path` before importing `sdk`.
- The official server token permits only one new server game. Use direct SDK practice games if needed, then spend the official server game carefully.
- Do not call `os.environ[...]`, `os.getenv(...)`, shell `echo`, `set`, `Get-ChildItem Env:`, or similar environment-dump commands for `ARCANE_LAB_*`; let `ArcaneLabServerSDK` read the runner-provided environment internally.
- Treat the official lifetime tick budget as a hard budget. Watch `observation["lifetime_tick"]` as well as the current run `tick`. If the official game reaches lifetime tick `240`, stop exploring, call `verify()`, and write the report. Do not continue official play beyond lifetime tick `260`.
- Do not print, dump, echo, log, manually set, or store the raw auth token anywhere. In particular,
  do not print runner auth variables or broad environment-variable dumps.

Random crit expectations:

- Official play should be through the server-backed SDK so every command, roll,
  and observation lands in `trajectory.json`.
- Random crit rolls are server/state seeded and visible after each `explore` in
  `observation["crit"]["last"]`.
- Use `list crit` or `observation["crit"]` for the current effective crit chance
  and attack bonus; buffs and equipment may change those values.
- You may adapt after observing rolls, but avoid strategies that rely on
  repeatedly creating official games.

Do not stop after a shallow early route if the prestige goal is still possible.
Continue adapting until one of these is true:

- `echo_vault_attuned` is complete and `echo_anchor` is crafted.
- The official run is near the runner lifetime tick budget and further progress would likely exceed it.
- The official game reaches lifetime tick `240`; at that point verify and report even if the prestige route is incomplete.
- Player-visible state shows no plausible legal path forward, and your report explains the blocker.

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

Then write a report to:

```text
logs\opencode_go_random_playtest_{{SAFE_MODEL}}_{{TIMESTAMP}}_report.md
```

The report must contain:

- model and runner if known
- whether the official attempt used server random crit mode
- official game id and verification result if available
- key commands or strategy
- final state
- whether `echo_vault_attuned` and `echo_anchor` were achieved
- notable random crit rolls that changed decisions
- any failed actions or confusing moments
- feedback on random crit mode, server SDK, gradual disclosure, and retire hints

Then print the report path and a concise result summary.
