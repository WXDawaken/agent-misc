---
id: playground.arcane_lab.tracks.pure-blind
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Pure Blind

Goal: discover Arcane Lab only through the prompt, SDK observations, player-visible
commands, and command outputs. Optimize for new systems discovered, completed
storylines, and final server reward without reading route notes, docs, source,
data, or helper scripts.

Track-specific play guidance:

- Treat the game as an unknown text RPG with a compact SDK interface.
- Use `observe()`, `status`, `list goals`, `list spells`, `list recipes`,
  `list areas`, `list buffs`, `list automation`, `list crit`, and normal
  game commands to build your model.
- Keep short notes under `logs\` as you infer mechanics.
- When a hypothesis fails, change one variable at a time before spending many
  more ticks.
- Do not treat the hidden token goal as known; infer likely goals from visible
  state and final verification only.

Verification:

At the end, call server-side `verify()` on the official game with no custom goal.
The token policy is authoritative.

Extra report fields:

- Mechanics you inferred from observations.
- Unlock conditions you believe you discovered.
- Which assumptions were wrong.
- What you would test next in a second pure-blind run.
