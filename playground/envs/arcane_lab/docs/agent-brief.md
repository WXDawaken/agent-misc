# Agent Brief

You are playing `Arcane Lab`, a text RPG about magical research. Most tasks use
deterministic rules; some official tasks may enable server-seeded pseudo-random
crit rolls.

Track runner profiles may include a local practice engine, but agent playtests
should use it only through the Python SDK. Do not invoke the command-line engine
directly and do not look for bundled or prewritten routes. For offline
practice, write a small helper under `logs\`:

```python
from sdk import ArcaneLabSDK

lab = ArcaneLabSDK(new=True)
print(lab.step("status").output)
```

Official tracked attempts use the replay server plus server-backed SDK. The
runner starts the server and provides credentials through the process
environment; do not start a server process yourself.

```python
from sdk import ArcaneLabServerSDK
lab = ArcaneLabServerSDK(new=True, label="agent-run")
print(lab.step("status").output)
```

For official tracked attempts, the runner provides server credentials through
the process environment and `ArcaneLabServerSDK` reads them automatically. Do
not inspect, print, copy, assign, or manually set those environment variables in
your scripts.

SDK notes:

- `lab.list_available(kind)` returns one newline-delimited string. Print it
  directly or call `.splitlines()` before iterating.
- `lab.observe()` returns dictionaries, for example
  `obs["elements"]["ember"]["level"]`, `obs["elements"]["ember"]["xp"]`,
  `obs["areas"]["training_yard"]["progress"]`, and
  `obs["areas"]["training_yard"]["clears"]`. Unlocked areas may also include
  a `boss` object with final-clear pressure mechanics and soft-counter hints.
  Equipment enhancement state is exposed as `obs["equipment_levels"]` and
  `obs["equipment_spares"]`.

Core commands:

- `status`: inspect current resources, stats, elements, areas, and buffs
- `list spells`: see castable spells
- `list recipes`: see transmutation recipes
- `list areas`: see exploration requirements, current combat stats, and visible boss soft counters
- `list goals`: see visible storyline goals and progress hints
- `list goals debug`: see all incomplete storyline conditions for verifier/debug work
- `list automation`: see active wizard assignments
- `list buffs`: see active buffs and remaining durations
- `list crit`: see the active crit mode and current effective crit values
- `list actions`: see active command tick costs
- `list reference`: see planning references, known buff durations, batch semantics, and route discipline
- `study <element> [turns]`: spend time and mana to level an element
- `cast <spell>`: manually cast a known spell
- `batch cast <spell[@priority] ...>`: cast multiple different spells in one action tick
- `explore <area> [times]`: attempt exploration
- `transmute <recipe> [count]`: craft equipment bonuses
- `enhance <recipe> [levels]`: combine spare +0 copies to improve a recipe stack
- `batch transmute <recipe[@priority] ...>`: try multiple different recipes in one action tick
- `hire [count]`: spend coins to hire wizards
- `assign <spell> <count>`: assign wizards to automated spells; use count `0` to stop one spell
- `unassign [spell ...]`: stop one or more automated spells, or all automation if no spell is given
- `tick [turns]`: advance passive mana and automation
- `retire`: reset the run for insight after retirement is unlocked

Crit modes:

- `charge` is the default mode. Successful non-critical explores add focus charge. At full charge, the next `explore` gets an attack bonus, spends all charge, and records the trigger in state. Charge carries across battles and resets on retirement.
- `random` uses a server/state seed and records every roll in the replay trajectory. Each `explore` checks the current chance and attack bonus shown by `list crit`. Official tasks should treat the server token as authoritative for this mode.

Useful early route:

1. Study Ember and Stone.
2. Use `Shape Pebble` to make ore.
3. Cast `Fire Lance`.
4. Clear the Training Yard.
5. Transmute a Focus Lens.
6. Hire a wizard and assign an automated spell.

Useful mid-game direction:

1. Clear Shaded Grove to open Sunken Stacks.
2. Study enough Ember and Gale to pass Sunken Stacks with batched buffs.
3. Clear Sunken Stacks to unlock Mind and `route_sketch`.
4. Use `route_sketch`, `tailwind`, and combat buffs to clear Gear Sanctum.
5. Build a `relic_frame`, then clear Prism Observatory to unlock Vital.
6. Watch final-clear boss hints in `list areas`; soft counters lower the
   effective final pressure, but enough raw attack/defense can still push through.

Equipment enhancement:

- Each recipe stack can be enhanced to `+n`; its effects are multiplied by
  `1.1 ** n`.
- After you own the normal `max_owned` copies of a recipe, extra `transmute`
  commands create spare +0 copies for enhancement.
- `enhance <recipe>` is instant and consumes spare +0 copies. The next levels cost 1, 2, 4,
  8, 16 spare copies by default, so deeper long-run enhancement gets expensive quickly.
- `list recipes` shows owned copies, current `+n`, multiplier, spare copies,
  and the next enhancement cost.

Automation spends mana every tick. If it blocks a planned cast or study route, pause it with `unassign <spell>` or `assign <spell> 0`.

Transcripts should be reproducible from the same save, command list, and crit mode/seed.

Storyline visibility is gradual. Normal play surfaces goals only after the relevant area, element, or automation concept is known. Distant storylines stay hidden until the route reaches them, while debug mode exists for benchmark authors and tuning.

Benchmark tasks usually limit lifetime game ticks, not command count. You may issue as many commands as needed for observation and planning, but actions that advance game ticks spend the budget. The current run tick resets on retirement; lifetime tick does not.

Action timing:

- `study`, `cast`, `explore`, `transmute`, and `hire` each take 1 tick.
- `enhance`, `assign`, `unassign`, `save`, and `retire` are instant.
- Wizard automation runs during action ticks, so automation can overlap with manual actions and consume mana before the manual action resolves.
- Exploration applies active buffs to the attempt, then decrements buff duration after the attempt.
- Batch commands use one action tick for the whole batch. Payloads resolve by explicit priority first, then original order. Use `spell@1` or `recipe@1` for higher priority. Duplicate payloads in one batch are rejected so each payload keeps separate state semantics.
If you need repeated copies of the same recipe, use `transmute <recipe> [count]` instead of duplicate batch payloads.

Retirement:

- `second_life` unlocks `retire`.
- Retiring starts the next run at tick `0`, resets resources, equipment, area clears, and element levels, then keeps completed storylines, permanent bonuses, discovered areas/elements, and insight.
- Insight increases max mana, mana rate, and study speed.
- After a full astral run, retiring with enough insight can reveal the second-run Echo Vault route.
