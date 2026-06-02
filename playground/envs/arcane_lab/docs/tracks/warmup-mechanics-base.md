---
id: playground.arcane_lab.tracks.warmup-mechanics-base
engine: mini-mustache
inputs:
  TRACK: string
---
Track phase: `{{TRACK}}` / Warmup Mechanics Base

Purpose: calibrate core Arcane Lab mechanics once, then leave compact notes for
later prestige solve attempts. This phase measures observation quality,
mechanics memory, and handoff hygiene. It should not solve or outline the full
prestige route.

Do not create an official server game in this phase. Do not call
`ArcaneLabServerSDK(new=True)`. Use only offline `ArcaneLabSDK` practice and
player-visible commands.

Hard rules:

- Use only the runner-provided workspace. Do not access or modify the parent
  source workspace.
- Do not spawn, launch, or delegate to subagents.
- Do not modify game code or data files.
- You may write only under `logs\`.
- You may read `README.md`, `docs\agent-brief.md`, and `docs\sdk-api.md` if
  they are present in the workspace.
- Do not read `docs\tasks.md` in this warmup phase. Save benchmark-target docs
  for the solve phase.
- Do not read or glob implementation/data files: `game.py`, `server.py`,
  `mcp_server.py`, `sdk\*.py`, or `data\*.json`.
- Do not use `list goals debug` or `goals_debug`.
- Do not read or run route/helper scripts under `scripts\*.txt`.
- Do not inspect, print, copy, assign, or manually set runner environment
  variables.
- If you write a temporary Python helper under `logs\`, insert the current
  workspace path into `sys.path` before importing `sdk`.

Warmup artifact contract:

- `logs\mechanics.md`: verified mechanics only. Include the evidence source
  for each point, such as a checkpoint, command output, or observed state.
  Mark guesses as `unverified` and disproven assumptions as `invalidated`.
- `logs\gotchas.md`: mistakes, ambiguous mechanics, random-crit observations,
  soft-stop/budget pitfalls, and any source-policy boundary that was easy to
  trip over. Keep each item paired with the corrected behavior.
- `logs\warmup_summary.md`: a short solve handoff. Summarize what is reliable,
  what remains unknown, and which assumptions a solve attempt should re-check.
  State explicitly that this warmup did not produce a prestige route candidate.

Keep artifacts compact enough to be useful as fork context. Do not paste long
transcripts, raw JSON dumps, or repeated full observations. Summarize only the
state that changes later decisions.

Warmup guidance:

- Treat this like a mechanics-check warmup, not a route-optimization pass.
- Exercise structured observations, batch command safety, action ticks,
  lifetime ticks, wizard automation, buff duration, exploration progress, and
  random crit reporting.
- It is fine to complete the early field-notes / focus-lens / wizard /
  `shaded_grove` mechanics route in offline practice.
- Stop before turning the session into late-game route discovery. Do not search
  for Astral, Echo, retirement timing, or full prestige route compression.
- Prefer a few bounded mechanics probes over open-ended scripts.
- When a probe fails, record the first real blocker and the corrected mechanic.

The handoff should reduce repeated mechanics rediscovery without seeding a
particular prestige route. Solve attempts may benefit from any files left in
`logs\`, but the stable contract is the three text artifacts above.
