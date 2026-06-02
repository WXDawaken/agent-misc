---
id: playground.arcane_lab.tracks.crit-build-eval
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Crit Build Evaluation

Goal: compare a crit-investing route against a crit-neutral route, then complete
or get as close as possible to the prestige Echo Vault target under the lifetime
tick budget.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

Evaluation guidance:

- Use player-visible interfaces only. You may read `docs\tasks.md` for
  benchmark-style task context, but do not read game/data/source files.
- In offline practice, build two compact route candidates:
  - a crit-investing route that intentionally uses player-visible crit-related
    spell or equipment options if you discover them;
  - a crit-neutral route that avoids optional crit-specific investments and uses
    normal combat, buffs, equipment, and route compression.
- Treat random crits as part of the official mode, but do not count lucky rolls
  as proof that a route is stable. Prefer comparing routes by repeatability,
  tick cost, command complexity, and whether the route still works when crits do
  not arrive at a gate.
- Use `list crit`, `list spells`, `list recipes`, `list areas`, and SDK
  observations to identify current effective crit values and route gates.
- Keep offline practice bounded. Once each route candidate has a clear result or
  blocker, stop broad exploration and choose one official route.
- Before creating the official server game, write `logs\crit_build_eval.md`
  with:
  - the tested crit-investing route summary and final tick/result;
  - the tested crit-neutral route summary and final tick/result;
  - which route you selected for the official attempt and why;
  - any uncertainty from random crit rolls.
- Before the official server game starts, write `logs\final_route.md` with the
  exact command blocks you will run officially. Keep it compact and route-like,
  not an exploratory script.
- Do not start the official game unless the chosen route has a plausible path to
  the target under the hard budget. If both candidates fail, submit the strongest
  partial route and explain the first missing gate.
- During official play, spend ticks only on the chosen route or on a short named
  recovery sequence whose remaining route still fits the hard budget. Use
  zero-tick observations to diagnose divergence.

Before the final report, explicitly evaluate:

- `echo_vault_attuned` completed?
- `echo_anchor` owned?
- `echo_vault` unlocked and cleared?
- retirements >= 1?
- insight >= 12?
- run >= 2?
- Did the crit-investing route beat the crit-neutral route on expected ticks or
  reliability?
- Did crit investment improve decisions, or mainly add planning overhead?

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

- Route selected for the official attempt: crit-investing or crit-neutral.
- Offline tick/result comparison for both candidates.
- Whether effective crit values were clear from the player-visible interface.
- Whether future agents should prefer, ignore, or situationally use crit
  investment.
