# Arcane Lab Design Notes

Arcane Lab is an original text RPG / incremental environment for agent testing. It is inspired by the broad genre shape of magic research games, especially the public description of Magic Research 2, but it avoids copying names, prose, exact progression, secrets, or numeric tables.

## Public Grounding

The Steam page for Magic Research 2 describes a single-player indie RPG/simulation released on 2024-05-21 by Maticolotto. Its public feature list emphasizes many spells, elemental study, item transmutation, wizard automation, semi-automated combat across exploration areas, storylines with permanent bonuses, and retirement bonuses.

Fan wiki pages also indicate that the game uses classes, storyline unlocks, elemental progression, exploration areas, and persistent rewards. Arcane Lab uses those as genre-level signals only.

## Mimic Scope

Arcane Lab currently models these systems:

- elemental study and level thresholds
- mana regeneration and manual spell casting
- wizard assignment for automation
- transmutation recipes, equipment bonuses, and equipment enhancement
- deterministic exploration checks
- area-clear boss pressure with visible soft-counter hints
- storyline unlocks, permanent bonuses, and gradual goal disclosure
- retirement as a prestige loop
- action timing where manual commands consume ticks while wizard automation overlaps
- batch actions for compatible same-verb payloads, with per-payload resolution and priority

The game intentionally uses original names:

- elements: Ember, Stone, Tide, Gale, Mind, Vital
- areas: Training Yard, Shaded Grove, Sunken Stacks, Gear Sanctum, Prism Observatory, Living Conduit, Astral Foundry, Echo Vault
- spells and recipes are original to this testbed

## Agent Evaluation Angles

Good tasks for an agent:

- infer next goals from `list goals`
- distinguish visible goals from hidden long-term storylines
- plan resource routes for a target recipe
- compare new equipment, spare +0 copies, and enhancement levels
- balance study, casting, exploration, and automation
- reason about action timing, buff duration, and automation overlap
- match area-clear boss pressure to targeted spells, active buffs, and equipment
- decide when batching compatible payloads is better than sequential actions
- recover after failed exploration
- decide when retirement is worth it
- summarize a playthrough from state and log

## Non-Goals

- no exact Magic Research 2 clone
- no copied in-game text
- no hidden spoiler database
- no external dependencies
- no real-time idle loop

The first version is small by design. It should be easy to extend by editing `data/arcane_lab.json` before changing engine code.

## Current Content Arc

- Early: Training Yard, Field Notes, Focus Lens, wizard automation.
- Mid: Shaded Grove into Sunken Stacks, Quiet Archive, Mind spells.
- Late-mid: Gear Sanctum into Prism Observatory, stronger route buffs, Vital unlock.
- Late: Living Conduit and Astral Foundry are present as harder targets for future playtests.
- Prestige: `second_life` unlocks retirement; after `astral_capstone`, retiring with enough insight reveals `echoed_foundation`, `echo_vault`, and the `echo_anchor` route.
