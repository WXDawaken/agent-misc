# Ledger Tower Tasks

## tutorial-clear

Reach floor `f3` within the move budget. This track checks basic map movement,
door/key use, fight previews, and stair routing.

Goal:

```json
{"floor": "f3"}
```

## ledger-clear

Clear the tower:

- defeat `f6_boss`
- collect `ledger_core`
- exit the final floor
- finish with at least 40 HP

Goal:

```json
{"victory": true, "boss": "f6_boss", "item": "ledger_core", "hp_min": 40}
```

## high-score

Clear the tower while preserving enough route score to show efficient choices.
The scoring function rewards victory, floor progress, HP, gold, stats,
artifacts, and lower move count. Remaining keys are a small tie-breaker, not a
primary route-quality signal.

Goal:

```json
{"victory": true, "item": "ledger_core", "hp_min": 40, "route_score_min": 14000}
```

## boss-gated-high-score

Clear the boss-gated map variant with the same high-score goal. The variant
places one boss on the mandatory route of every floor, so combat is enforced by
layout instead of by adding extra goal keys.

Goal:

```json
{"victory": true, "item": "ledger_core", "hp_min": 40, "route_score_min": 14000}
```
