# Arcane Lab Benchmark Task Sketches

These are small local tasks in the style of RuneBench task prompts. They are not Harbor tasks yet, but the SDK/MCP/verifier are ready for that direction.

## Task: Field Notes

Goal: complete storyline `field_notes`.

Suggested verifier:

```python
lab.verify({"storyline": "field_notes"}, tick_budget=18)
```

## Task: Automation Baseline

Goal: own one `focus_lens`, hire one wizard, and assign `shape_pebble`.

Suggested verifier:

```python
lab.verify({"recipe": "focus_lens", "wizards": 1, "assignment": "shape_pebble"}, tick_budget=25)
```

## Task: Shaded Grove Entry

Goal: unlock and make progress in `shaded_grove`.

Suggested verifier:

```python
lab.verify({"area": "shaded_grove", "area_clears": 1}, tick_budget=35)
```

For partial progress without requiring a full clear:

```python
lab.verify({"area_progress": {"area": "shaded_grove", "target": 2}}, tick_budget=25)
```

Server-side verification writes the official `verification.json`; read the
returned goal completion fields for budget and goal details.

There is no command-count limit in these sketches. The budget is lifetime game tick, so batching compatible actions can matter. The current run tick remains a separate metric and can be constrained with `--per-run-tick-budget` for tasks that need that shape.

## Task: Living Formula

Goal: clear `prism_observatory` once and unlock the `living_formula` storyline.

Suggested verifier:

```python
lab.verify({"storyline": "living_formula", "area": "prism_observatory", "area_clears": 1}, tick_budget=85)
```

This task expects agents to chain early automation, batch buffs, Quiet Archive, Gear Sanctum, and the new Prism Observatory route.

## Task: Astral Capstone

Goal: clear `astral_foundry` once and unlock the `astral_capstone` storyline.

Suggested verifier:

```python
lab.verify({"storyline": "astral_capstone", "area": "astral_foundry", "area_clears": 1}, tick_budget=220)
```

The reference playtest route finishes at tick `216`; a budget of `215` is expected to fail only on the tick budget.

## Task: Retirement State

Goal: retire once, keep at least `12` insight, reach run `2`, and preserve late area unlocks.

Suggested verifier:

```python
lab.verify({
    "retirements": 1,
    "insight": 12,
    "run": 2,
    "unlocked_areas": ["sunken_stacks", "gear_sanctum", "astral_foundry", "echo_vault"],
})
```

This task can now use `--tick-budget` for route speed because lifetime tick persists across retirement. Leave it off when testing prestige-state consistency rather than efficiency.

## Task: Echo Vault

Goal: retire after the first full astral run, reveal `echoed_foundation`, clear `echo_vault`, complete `echo_vault_attuned`, and craft `echo_anchor`.

Suggested verifier:

```python
lab.verify({
    "storyline": "echo_vault_attuned",
    "area": "echo_vault",
    "area_clears": 1,
    "recipe": "echo_anchor",
    "retirements": 1,
    "insight": 12,
    "run": 2,
})
```

The reference prestige route reaches run `2`, clears `echo_vault`, and crafts `echo_anchor` at run tick `6` / lifetime tick `222`; the full route still requires the long first-run capstone setup before retirement, so use lifetime tick for official route budgets.

## Agent Instructions Pattern

Use short iterations:

1. Observe with SDK/MCP.
2. Try one command.
3. Observe the result.
4. Extend only after the action works.

Avoid one giant script until a route is proven.
