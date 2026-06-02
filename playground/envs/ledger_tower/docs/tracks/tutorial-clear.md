---
id: playground.ledger_tower.tracks.tutorial-clear
engine: mini-mustache
inputs:
  TICK_BUDGET: int
  REPORT_PATH: string
---
# Track: tutorial-clear

Reach floor `f3` within the hard move budget of `{{TICK_BUDGET}}`.

You may use offline practice if available. Focus on proving the mechanics:
movement, one yellow door, combat preview, a blue key, and stairs.

Official verification:

```python
verification = tower.verify()
```

The token already carries the track goal.
