---
id: playground.arcane_lab.tracks.budgeted-prestige
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Budgeted Prestige

Goal: use player-visible interfaces to discover and complete, or get as close as
possible to, the prestige Echo Vault route while staying under the lifetime tick
budget.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

Track-specific play guidance:

- You may also read `docs\tasks.md` for benchmark-style task context.
- Before creating the official server game, use offline practice to prove a
  complete end-to-end route from a new game through `echo_vault_attuned` and
  `echo_anchor`; do not spend the official new game on a partial mid-route
  milestone.
- Keep offline practice bounded. Once you have one complete route that reaches
  all target outcomes under the hard budget, stop broad exploration. You may do
  at most one targeted repair or compression pass for a named issue, such as
  integrating retirement element levels before Astral Foundry to improve the
  soft-stop score.
- Before calling `ArcaneLabServerSDK(new=True)`, write `logs\final_route.md`.
  Keep it compact and make it the source of truth for the official attempt.
  It must include:
  - ordered command blocks for the official run,
  - expected lifetime tick checkpoints for Training/Shaded, Sunken, Gear,
    Prism, Living/Astral, retirement, and Echo,
  - required stats, buffs, equipment, and counters for boss gates,
  - exact stop or pivot conditions if a checkpoint slips.
- `logs\final_route.md` is not valid if any required late route is marked
  `TBD`, `discover after`, or otherwise left to official exploration. It must
  name the exact Astral Foundry, retirement, Echo Vault, and `echo_anchor`
  command blocks before the official game starts.
- Do not start the official run unless `logs\final_route.md` leaves a safety
  margin under the hard budget and names the post-retirement Echo commands. If
  offline practice cannot reach the full target, report that and preserve the
  official attempt instead of converting it into exploration.
- If the proven route misses only the soft-stop line but still reaches all
  target outcomes under the hard budget, prefer running the official route over
  unbounded optimization. Report the soft-stop tradeoff and any single known
  optimization opportunity.
- At every 25 lifetime ticks, checkpoint whether your next commands directly
  advance the prestige goal.
- If you cannot name the missing unlock condition, observe with `list goals`,
  `list areas`, `list spells`, and `list recipes` instead of grinding.
- Do not stop after a shallow early route if the prestige goal is still possible.
- During official play, update only a small `logs\official_status.md` with
  current checkpoint deltas. If the official state diverges from
  `logs\final_route.md`, compare against the route plan and avoid ad hoc
  grinding.
- After the official game starts, do not run tick-spending diagnostic scripts to
  test unknown requirements, unknown buffs, or possible boss counters. Only use
  zero-tick observations such as `observe()`, `status`, `list areas`, `list
  spells`, `list recipes`, `list buffs`, and `list goals` to diagnose a
  divergence. Any official tick-spending command should either come from
  `logs\final_route.md` or be a short named recovery sequence whose remaining
  route still fits the hard budget.
- If you reach the soft-stop line with only a known final target action left
  (for example crafting `echo_anchor`), finish the target while staying under
  the hard budget and report the soft-stop tradeoff.
- At or after the soft stop, continue only when the remaining command sequence
  from the current checkpoint to the final target fits the hard budget.
  Otherwise stop immediately, call `verify()` for the partial official result,
  and report the first missing gate.
- Continue adapting until one of these is true:
  - `echo_vault_attuned` is complete and `echo_anchor` is crafted.
  - The official game is near the lifetime tick budget and further progress would likely exceed it.
  - Player-visible state shows no plausible legal path forward, and your report explains the blocker.

Before the final report, explicitly evaluate:

- `echo_vault_attuned` completed?
- `echo_anchor` owned?
- `echo_vault` unlocked and cleared?
- retirements >= 1?
- insight >= 12?
- run >= 2?

Do not describe the run as successful unless `echo_vault_attuned` is complete
and `echo_anchor` is owned.

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
- Checkpoint decisions, especially whether/when to retire.
