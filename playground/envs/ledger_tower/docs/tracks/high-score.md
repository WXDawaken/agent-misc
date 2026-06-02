---
id: playground.ledger_tower.tracks.high-score
engine: mini-mustache
inputs:
  TICK_BUDGET: int
  SOFT_STOP_TICK: string
  ROUTE_SCORE_MIN: int
  REPORT_PATH: string
---
# Track: high-score

Clear Ledger Tower while preserving a strong route score.

Hard budget: `{{TICK_BUDGET}}`
Soft stop: `{{SOFT_STOP_TICK}}`

The goal requires victory, `ledger_core`, at least 40 HP, and a route score of
at least `{{ROUTE_SCORE_MIN}}`. Avoid unnecessary fights, wandering, and
low-value purchases; the route score now uses a heavier movement penalty, so
compact routes matter.
When a high-score track enables soft stop, compliance is scored linearly from
`1` at the soft stop to `0` at the hard budget; it is advisory and does not
change verification reward.

Official verification:

```python
verification = tower.verify()
```

The token already carries the track goal.
