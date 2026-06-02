# Ledger Tower Design

Last updated: `2026-05-20`

## Capability Axis

Ledger Tower adds exact finite-resource spatial optimization beyond Arcane Lab.
It asks agents to maintain a small but unforgiving ledger of HP, attack,
defense, gold, keys, doors, and map position. There is no hidden randomness and
no grinding; route order is the puzzle.

## Originality

The environment uses only genre-level ideas from fixed-value tower puzzle RPGs.
All floor names, enemy names, item names, maps, numbers, goals, and prose are
bespoke for this workspace.

## Smallest Deterministic Version

The first version is a six-floor, 9x9 tower with:

- visible maps
- visible monster handbook
- deterministic fight previews
- yellow and blue keys
- doors, shops, stat gems, potions, and one final artifact
- one final boss and exit

## Current Map Property

The current fixed 9x9 map can be cleared without combat. Agents can reach
`ledger_core` and the exit while bypassing `f6_boss`; combat is required only by
tracks whose goal explicitly names a boss or other defeated enemy condition.

This is a useful benchmark signal rather than an accidental test failure: the
same map can distinguish agents that optimize for clean, soft-stop-respecting
no-combat clears from agents that use combat and shop conversion to maximize
reward. If a future benchmark needs combat to be structurally unavoidable, build
a separate map or track variant instead of assuming the current layout enforces
that route shape.

The `boss_gated` variant is the combat-required counterpart. Each floor boss is
placed on a structural cut point between the entry-side zone and the upward or
exit-side zone. Its optional side routes are designed as explicit tradeoffs:
early blue-key detour versus later shortcut, high-risk attack pickup, HP/gold
conversion, and defense/gold conversion before the final audit.

## Generated Variants

Further variants should be generated topology-first: graph grammar, then grid
embedding, then solver scoring. This keeps spatial variety subordinate to route
economy. The first local generator is documented in
`docs\variant-generation.md`; it currently emits `branchy_score`,
`shop_timing`, and `key_pressure` candidates into runtime logs for review before
any map is promoted into `data\`. Its default embedding is a hybrid room/corridor
style: less fragmented than tree growth, but less blob-like than broad room
patches.

## Budget Metric

The official budget metric is `moves`.

Free commands:

- `status`
- `map`
- `list`
- `preview`

Budget-spending commands:

- `move`, including fights, doors, item pickups, stairs, and exit
- `buy`, with each purchase costing one move

## Observation Surface

Observations expose current floor, position, HP, attack, defense, gold, keys,
inventory, floor map, active current-floor entities, enemy handbook, shop
offers, available commands, score, and optional budget state.

## First Tracks

- `tutorial-clear`: reach floor `f3` under a generous move budget.
- `ledger-clear`: defeat the final boss, collect `ledger_core`, exit, and keep
  enough HP.
- `high-score`: clear the same tower while preserving a higher route score.

The `core` suite keeps the fixed default map for baseline comparisons. Tracks
that change disclosure, practice budget, official-attempt count, or map topology
belong in `extended` suites. Generated or variant maps can use floor-count-aware
goals: `final_floor`, `final_boss`, and numeric targets such as
`route_score_min = base + per_floor * floor_count`. The current high-score target
uses `9800 + 700 * floor_count`, which resolves to the historical `14000` on the
six-floor default maps.

## Success And Partial Credit

Official verification accepts runs that stay within the hard move budget.
Success requires all track goals. Partial means the run stayed within the hard
budget but missed one or more goals. Rejected means a hard policy failed, such
as exceeding the move budget.
