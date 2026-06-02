---
id: playground.arcane_lab.tracks.route-optimization
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Route Optimization

Goal: complete `echo_vault_attuned` and craft `echo_anchor` efficiently under
the lifetime tick budget. This track gives high-level route milestones but still
requires you to execute the route yourself.

High-level route hints:

- You may also read `docs\tasks.md` for benchmark-style task context.
- Build the early economy and automation baseline.
- Clear Training Yard, Shaded Grove, Sunken Stacks, Gear Sanctum, Prism Observatory, Living Conduit, and Astral Foundry.
- Use batch casts for compatible buffs; one batch costs one action tick.
- Clearing the full Astral Foundry route enables the prestige setup.
- Retire after the first full astral run when the next run can reveal the echo route.
- In run 2, use the preserved unlocks and insight to clear Echo Vault and craft Echo Anchor.

Optimization priorities:

- Favor batched compatible casts/transmutes over sequential actions when the payloads do not conflict.
- Avoid repeating failed explores unless a concrete stat, buff, crit state, or resource condition changed.
- Retire as a strategic step once the first-run route has produced enough durable progress; do not keep grinding a solved run.
- Track both `lifetime_tick` and current run `tick` in your notes.
- Use random crits opportunistically, but do not build a plan that requires a lucky roll.
- At every 25 lifetime ticks, checkpoint whether your next commands directly advance the route.

Before the final report, explicitly evaluate:

- `echo_vault_attuned` completed?
- `echo_anchor` owned?
- `echo_vault` unlocked and cleared?
- retirements >= 1?
- insight >= 12?
- run >= 2?

Verification:

At the end, call server-side `verify()` on the official game with this goal:

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

Extra report fields:

- Whether `echo_vault_attuned` and `echo_anchor` were achieved.
- Route plan, key command groups, and optimization choices.
- What still seems inefficient.
