---
id: playground.ledger_tower.tracks.ledger-clear
engine: mini-mustache
inputs:
  TICK_BUDGET: int
  REPORT_PATH: string
---
# Track: ledger-clear

Clear Ledger Tower within the hard move budget of `{{TICK_BUDGET}}`.

The goal is to defeat `f6_boss`, collect `ledger_core`, exit the final floor,
and finish with at least 40 HP.

Use `preview` aggressively. Shop choices are part of the puzzle; buying only the
locally appealing stat can make the final boss impossible.

Official verification:

```python
verification = tower.verify()
```

The token already carries the track goal.
