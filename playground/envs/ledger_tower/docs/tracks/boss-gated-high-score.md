---
id: playground.ledger_tower.tracks.boss-gated-high-score
engine: mini-mustache
inputs:
  TICK_BUDGET: int
  SOFT_STOP_PROFILE: string
  ROUTE_SCORE_MIN: int
  FLOOR_COUNT: int
  REPORT_PATH: string
---
# Track: boss-gated-high-score

Clear the boss-gated Ledger Tower variant while preserving a strong route
score.

Hard budget: `{{TICK_BUDGET}}`
Soft stop: `{{SOFT_STOP_PROFILE}}`

This track uses a variant map selected by the runner. The selected map has
`{{FLOOR_COUNT}}` ordered floors. Each floor has a boss on
the mandatory route upward, so high score should come from sequencing, shop
timing, and resource preservation rather than bypassing all combat.

The goal requires victory, `ledger_core`, at least 40 HP, and a route score of
at least `{{ROUTE_SCORE_MIN}}`. Avoid unnecessary detours and low-value
purchases; the route score uses the current `-30` movement penalty, so compact
routes matter. This variant has no soft-stop compliance target; route quality
should be judged by the verification reward, route score, and hard-budget
legality.

Official verification:

```python
verification = tower.verify()
```

The token already carries the track goal.
