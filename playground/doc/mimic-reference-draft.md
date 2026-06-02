# Mimic Reference Draft

Last updated: `2026-05-11`

This is a draft research summary for possible `playground` game environments that complement `Arcane Lab`. It is not a commitment to build every item here.

## Frame

`Arcane Lab` already covers long-horizon resource routing, spell/buff timing, automation, equipment choices, retirement/prestige, and official-run discipline. The next game environments should be mechanically orthogonal where possible:

- spatial state tracking
- exact finite-resource optimization
- partial observability
- evidence synthesis
- constructive system design
- stochastic build robustness
- protocol/manual following

The intended approach is genre-level mimicry only. Do not copy names, maps, prose, art, exact numeric tables, unique story beats, or spoiler-heavy progression from the reference games.

## Priority Candidates

### 1. Magic Tower-like / Fixed-Value Puzzle RPG

Working benchmark idea: `Ledger Tower` or `Crystal Keep`.

Reference objects:

- [Magic Tower / Tower of the Sorcerer](https://zh.wikipedia.org/wiki/%E9%AD%94%E5%A1%94): origin point for the fixed-value tower puzzle RPG shape.
- [Magic Tower game genre](https://zh.wikipedia.org/wiki/%E9%AD%94%E5%A1%94%E6%B8%B8%E6%88%8F): describes the broader Chinese lineage as fixed-value RPG.
- [Mota Wiki genre notes](https://mota.fandom.com/zh/wiki/%E9%AD%94%E5%A1%94): useful community summary of time-independence, repeatability, discreteness, boundedness, and multi-variable resource systems.
- [Tactical Nexus](https://store.steampowered.com/app/1141290/Tactical_Nexus/): modern Magic Tower-inspired resource-management puzzle RPG.
- [DROD RPG: Tendry's Tale](https://store.steampowered.com/app/351330/DROD_RPG_Tendrys_Tale/): deterministic puzzle dungeon crawl with RPG stats and resource management.
- [Desktop Dungeons](https://store.steampowered.com/app/226620/Desktop_Dungeons/): adjacent quick-play puzzle roguelike where exploration itself is a resource.
- [mota-js](https://github.com/ckcz123/mota-js) and [H5Mota](https://mota.games/): ecosystem references for editor, replay, monster handbook, damage preview, and leaderboard expectations.

Why it complements `Arcane Lab`:

- It tests exact arithmetic and order-of-operations more sharply than Arcane Lab.
- It is finite, deterministic, and replayable, so verification is straightforward.
- It exposes whether an agent can maintain a spatial/resource ledger without drifting.
- It can be made small enough for short tracks while retaining real optimization depth.

Core mechanics to mimic:

- Fixed grid floors, stairs, doors, keys, potions, gems, shops, and finite monsters.
- Player stats: `hp`, `atk`, `def`, `gold`, key counts, and optional special items.
- Enemy stats: deterministic damage preview from `hp/atk/def/gold`.
- Order-sensitive tradeoffs: fight now versus later, open this door versus save the key, buy attack versus defense.
- Optional score targets: clear, final HP, remaining keys, gold efficiency, optional boss, route length.

First viable benchmark:

- 6 to 10 floors, each 9x9 or 11x11.
- No randomness.
- Visible monster handbook.
- SDK commands: `observe`, `move`, `preview_fight`, `route_replay`, `verify`.
- Tracks:
  - `tutorial-clear`: finish a small tower.
  - `ledger-clear`: finish while keeping enough HP and keys.
  - `high-score`: optimize final score.
  - `limited-preview`: restrict or charge for preview calls to test internal calculation.

This is the strongest near-term addition.

### 2. Grid Tactics / Partial-Info Drone Exploration

Working benchmark idea: `Grid Relic`.

Reference objects:

- [Into the Breach](https://subsetgames.com/itb.html): compact turn-based grid tactics, telegraphed enemy actions, protection objectives.
- [Duskers](https://store.steampowered.com/app/254320/Duskers/): command-line drone control, partial sensors, salvage, and survival under uncertainty.

Why it complements `Arcane Lab`:

- Adds spatial reasoning, local tactical search, and multi-unit planning.
- Tests whether the agent can track positions, hazards, line of sight, and delayed consequences.
- Duskers-like command control is especially compatible with text/SDK play.

Core mechanics to mimic:

- Small grid maps with walls, doors, hazards, enemies, and objectives.
- Enemy intent preview for some tracks; hidden enemy state for harder tracks.
- Limited tools: shove, shield, scan, lure, repair, unlock, extract.
- Scoring by survival, objective completion, turns, collateral damage, and salvage.

Recommended shape:

- Start deterministic and fully replayable.
- Add partial observability only after the basic tactical verifier is solid.
- Avoid real-time pressure; use turn budgets instead.

### 3. Deduction Board / Evidence Reconstruction

Working benchmark idea: `Caseboard`.

Reference objects:

- [The Case of the Golden Idol](https://store.steampowered.com/app/1677770/The_Case_of_the_Golden_Idol/): scene investigation, suspect/motive/weapon deduction, term collection.
- [Return of the Obra Dinn](https://store.steampowered.com/app/653530/Return_of_the_Obra_Dinn/): exploration plus logical deduction over identities, causes, and events.

Why it complements `Arcane Lab`:

- Tests hypothesis management rather than action routing.
- Rewards evidence citation and delayed commitment.
- Easy to score with structured answers.

Core mechanics to mimic:

- Text scenes, objects, witness statements, timelines, and a controlled vocabulary.
- Final answer forms: `person`, `role`, `location`, `action`, `motive`, `cause`.
- Verification checks both exact solution and evidence-backed partial progress.

Recommended shape:

- Keep scenes small but interdependent.
- Include decoy clues and ambiguous early hypotheses.
- Require a short evidence note for each final claim.

### 4. Factory / Logistics / Constructive Puzzle

Working benchmark idea: `Foundry Lines`.

Reference objects:

- [Factorio](https://www.factorio.com/game/content): mining, logistics, production, power, research, blueprints, circuit-like control.
- [Opus Magnum](https://www.zachtronics.com/opus-magnum/): open-ended machine construction scored by speed, cost, and footprint.
- [Mini Metro](https://dinopoloclub.com/games/mini-metro/): dynamic network design with limited resources and congestion pressure.

Why it complements `Arcane Lab`:

- Moves from route selection to building a working system.
- Tests constraint satisfaction, throughput reasoning, and compact artifact generation.
- Produces measurable artifacts: layouts, machines, connections, tick output.

Core mechanics to mimic:

- A small grid with sources, sinks, machines, belts/pipes, and power.
- Recipes with input/output rates.
- Scoring by correctness, throughput, cost, footprint, and stability over N ticks.

Recommended shape:

- Start closer to Opus Magnum/Factorio micro-puzzles than a full factory sim.
- Avoid free-form geometry explosion in the first pass.
- Make the verifier simulate the submitted layout deterministically.

### 5. Deckbuilder / Buildcraft Combat

Working benchmark idea: `Rune Deck`.

Reference object:

- [Slay the Spire](https://store.steampowered.com/app/646570/Slay_the_Spire/): roguelike deckbuilding with card choices, relic synergies, changing paths, and turn-based combat.

Why it complements `Arcane Lab`:

- Tests probabilistic planning and synergy evaluation.
- Creates controlled stochastic variants through seeded card rewards and enemy behavior.

Reasons to defer:

- Balance is expensive.
- Poor tuning can turn the benchmark into luck or rote policy.
- The state/action space grows quickly.

Recommended shape:

- Use fixed seeds and small decks first.
- Score expected robustness across several seeds only after a deterministic baseline works.

### 6. Manual / Protocol Puzzle

Working benchmark idea: `Module Desk`.

Reference object:

- [Keep Talking and Nobody Explodes](https://keeptalkinggame.com/): modular puzzles, external manual, communication and time pressure.

Why it complements `Arcane Lab`:

- Tests document lookup, procedural compliance, and concise reporting.
- Can also become a multi-agent benchmark later.

Recommended shape:

- Single-agent text version first: the agent sees module facts and must apply a manual.
- Later: split defuser/expert roles across subagents.
- Use turn or mistake budgets, not real-time timers.

### 7. Dynamic Rule Puzzle

Working benchmark idea: `Rule Blocks`.

Reference object:

- [Baba Is You](https://store.steampowered.com/app/736260/Baba_Is_You/): rules are represented as movable blocks; changing them changes level logic.

Why it complements `Arcane Lab`:

- Tests rule induction and counterintuitive reasoning.

Reasons to defer:

- It is easy to write puzzles that become author-intent guessing.
- Verifier and level generator need careful design.

Recommended shape:

- Use very small rule vocabularies.
- Expose the active rule table directly.
- Make solutions replayable as move sequences.

## Proposed Suite Shape

A balanced future benchmark suite could be:

- `Arcane Lab`: long-horizon incremental RPG planning.
- `Ledger Tower`: exact finite-resource spatial optimization.
- `Grid Relic`: tactical grid state and partial observability.
- `Caseboard`: evidence synthesis and structured deduction.
- `Foundry Lines`: constructive logistics and throughput design.

This covers arithmetic/resource ledgers, spatial memory, route planning, evidence reasoning, and artifact construction without requiring a huge commercial-game-sized implementation.

## Safety And Originality Rules

- Use references only for public genre-level mechanics.
- Do not copy maps, enemy tables, recipes, names, prose, UI art, puzzle layouts, or story beats.
- Prefer original names, original numeric tuning, and small bespoke content.
- Keep tasks deterministic or server-seeded.
- Persist trajectories and verification outputs.
- Provide SDK/MCP-style interfaces before asking agents to solve official tracks.
- Keep benchmark docs player-facing; keep source, smoke scripts, and known routes out of isolated official workspaces when a track is meant to test discovery.
- For fixed-map optimization tracks, separate whitebox practice, server-token
  practice budgets, and official attempts explicitly. If more than one official
  attempt is granted, score the best verified independent official-game
  submission for that task; a verified official game is closed to further play.

## Recommendation

Build `Ledger Tower` first.

It has the best ratio of implementation cost to benchmark value: small deterministic engine, easy replay, rich optimization, and a clear capability gap relative to `Arcane Lab`. A first version can be data-driven like `Arcane Lab`, with floors, entities, enemies, and item effects in JSON and a compact Python engine plus SDK/verifier.

After `Ledger Tower`, build either `Grid Relic` for spatial tactics or `Caseboard` for evidence reasoning, depending on whether the next desired capability axis is action planning or non-action inference.
