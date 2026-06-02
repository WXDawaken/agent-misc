# Ledger Tower Variant Generation

Last updated: `2026-05-20`

## Purpose

Ledger Tower variants should test route planning, resource timing, and strategic
preference. The generator therefore treats the grid as the final embedding
layer, not as the main source of difficulty.

The first generator is:

```text
graph grammar -> grid embedding -> map validation -> solver scoring -> report
```

It lives at:

```powershell
python envs\ledger_tower\scripts\generate_variants.py
```

Generated candidates are runtime artifacts under
`logs\ledger_variant_generation\...` by default. Promote a candidate into
`envs\ledger_tower\data\` only after reviewing the report, route scripts, and
map shape.

## Grammar Shape

The generator builds each floor from a small topology:

- a forward entry cell
- a boss-bearing spine node
- a post-boss exit or upward stair
- optional branches before and after the boss
- optional shops, keys, doors, and high-risk reward branches

The default generated grid is `11x11`, but the main spine remains compact. Extra
grid area is used mostly for small rooms, widened corridors, side branches, and
short loops, so variants do not become pure walking-cost tests. The default
target open-cell ratio is `0.42`. General generated variants use
`--boss-gate-mode relaxed`, where bosses may be bypassed if the room layout
permits it. Use `--boss-gate-mode preserve` only for variants that intentionally
need every floor boss to be a structural cut point.

The default tower height is `--floors 6`. Alternate floor counts are generated
by mapping each floor onto the existing six-stage Ledger progression: the first
floor uses the entry role, the final floor uses the final-audit role, and middle
floors are interpolated across the current item, boss, key-door, and shop timing
tables. This keeps 4-floor, 6-floor, and 8-floor orchestration variants on the
same economy scale while avoiding separate hand-authored tables for each height.

## Placement

Primary resources, shops, and the final core are placed after spine, branch, and
room carving. The placer still respects each entity's intended before-boss or
after-boss side, but it chooses from open cells associated with that spine
segment instead of only from the spine itself. This lets generated rooms and
side pockets absorb resources instead of forcing short segments into visible
resource strings.

The current primary-placement rule prefers a minimum Manhattan distance of `3`
from the boss gate and from already placed resources/shops, plus a softer
minimum distance of `2` from stairs, exits, and entry/finish structural points.
If a compact floor cannot satisfy those thresholds, placement relaxes them
rather than rejecting the whole candidate. Once candidates satisfy the active
thresholds, the placer samples randomly instead of always taking the farthest
cell, avoiding both resource strings and excessive corner rewards. Per-floor
generation metadata records the number of primary placement choices, any
relaxed choices, and the lowest accepted resource/structural distances.

## Space Styles

The default `--space-style hybrid` is the current middle ground between narrow
tree maps and broad room-patch maps. It opens small rooms around structural
nodes such as stairs, exits, the boss gate, and selected spine points; lightly
widens corridors; fills remaining space through a limited frontier; and adds a
small number of short loops via `--loop-budget`.

Other styles remain available for targeted probes:

- `tree`: single-neighbor frontier growth; useful when preserving boss cuts is
  the priority.
- `patch`: room patches around existing open cells; useful for intentionally
  open exploratory layouts.
- `hybrid` plus `--boss-gate-mode preserve`: keeps the hybrid room/corridor
  feel where possible while rejecting openings that would break the boss cut.

## Current Profiles

- `branchy_score`: optional score branches around a mandatory boss spine.
- `shop_timing`: earlier shop pressure plus gold/resource branches before
  purchase decisions.
- `key_pressure`: carried yellow-key gates plus optional blue-key/blue-door
  reward branches.

These profiles are intentionally coarse. A candidate is only useful if the
solver finds it playable and the report shows multiple plausible route shapes.

## Validation

The generator validates:

- rectangular floor grids
- entity coordinates in bounds and off walls
- no duplicate entity coordinates
- item, enemy, door, shop, and stair references
- stair target legality
- static reachability from known entry points
- when `--boss-gate-mode preserve` is selected, whether each generated floor
  boss is a structural cut point on the forward route

Warnings do not automatically reject a candidate, but a promoted benchmark map
should have no structural warnings unless the variant explicitly wants them.

## Solver Scorer

The scorer reuses the Ledger Tower engine instead of reimplementing combat.
It runs a best-first macro search over:

- shortest reachable paths to active entities
- one-step shop buys when standing on a shop
- the normal `high-score` goal shape

Candidate ranking favors:

- playable successful routes
- higher best route score
- route-score spread among successful routes
- multiple route shapes

The solver is a screening tool, not a proof of optimality. Promoted candidates
still need agent playtests.

## Example

```powershell
python envs\ledger_tower\scripts\generate_variants.py `
  --count 2 `
  --profiles branchy_score,shop_timing,key_pressure `
  --floors 6 `
  --width 11 `
  --height 11 `
  --open-ratio 0.42 `
  --space-style hybrid `
  --loop-budget 1 `
  --boss-gate-mode relaxed `
  --budget 80 `
  --beam-width 1600 `
  --max-expansions 25000 `
  --keep 5
```

The output directory contains:

- `summary.json`: machine-readable candidate scores
- `report.md`: table summary for quick review
- `<candidate>.json`: kept candidate data files
- `<candidate>_best_route.txt`: solver's best found route

Selection keeps at least one playable candidate per requested profile by
default via `--keep-per-profile 1`, then fills the remaining slots by ranking.
This prevents lower-scoring but strategically distinct profiles from being
hidden by a single high-scoring family.

## Promotion Checklist

Before creating a track from a generated candidate:

- inspect the map visually with `map all`
- replay the best route through the SDK
- confirm the hard budget matches the route family
- decide whether the score formula should be disclosed
- decide whether the track permits whitebox, practice-token, or no-practice
  play
- run at least GPT and one non-GPT model before treating the candidate as a
  benchmark map

## Promoted Candidates

- `generated-shop-timing-8f-high-score` now promotes
  `logs\ledger_variant_generation\placement_random_eligible_smoke\shop_timing_001.json`
  into `envs\ledger_tower\data\ledger_tower_generated_shop_timing_8f.json`,
  replacing the earlier `20260520_050329\shop_timing_001.json` promotion. The
  replacement screening solver found a best route with route score `15880`,
  verification reward `25380`, and `113/125` moves on an 8-floor, 13x13 hybrid
  layout with wider resource spacing. This track is intentionally `extended`,
  not `core`; it keeps whitebox practice and formula disclosure for initial
  cross-model testing.
