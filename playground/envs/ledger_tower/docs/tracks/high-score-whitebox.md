---
id: playground.ledger_tower.tracks.high-score-whitebox
engine: mini-mustache
inputs:
  TICK_BUDGET: int
  SOFT_STOP_TICK: string
  ROUTE_SCORE_MIN: int
  FLOOR_COUNT: int
  FINAL_BOSS: string
  REPORT_PATH: string
---
# Track: high-score-whitebox

Clear Ledger Tower while optimizing the disclosed high-score formula.

Hard budget: `{{TICK_BUDGET}}`
Soft stop: `{{SOFT_STOP_TICK}}`

The goal requires victory, `ledger_core`, at least 40 HP, and a route score of
at least `{{ROUTE_SCORE_MIN}}`.

## Disclosed Scoring

`route_score` is:

```text
(10000 if victory else 0)
+ floor_number * 700
+ hp * 3
+ gold * 20
+ atk * 50
+ def * 50
+ key_value * 30
+ artifacts * 1000
- moves * 30
```

where:

- `floor_number` is the current ordered floor index. This selected map has
  `{{FLOOR_COUNT}}` floor(s).
- `key_value = yellow_keys + 2 * blue_keys + 3 * red_keys`.
- `artifacts` is the inventory artifact count; `ledger_core` counts as one.
- Defeated enemies, opened doors, and collected item count are reported metrics
  but do not directly add score except through HP, gold, stats, keys, artifacts,
  floor, victory, and moves.

For a successful in-budget high-score verification, the final verification
reward is `route_score + 9500`:

```text
+5000 victory
+2500 ledger_core
+1000 hp_min
+1000 route_score_min
```

If the hard move budget is exceeded, verification reward is zero. When soft stop
is enabled, it is a route-quality/compliance signal, not a separate
verification-reward term; `route_score` already charges every move at `-30`.
For soft-stop-enabled high-score tracks, `softStopScore` linearly decays from
`1` at the soft stop to `0` at the hard budget.

The high-score goal does not require defeating the final boss
`{{FINAL_BOSS}}`. A boss fight is useful only if its resource gains improve the
formula enough to justify the HP and move cost.

Official verification:

```python
verification = tower.verify()
```

The token already carries the track goal.
