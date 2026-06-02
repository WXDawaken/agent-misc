---
id: playground.arcane_lab.tracks.blind-discovery
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Blind Discovery

Goal: discover the game through player-visible interfaces and push as far as you
can within the official lifetime tick budget. Optimize for completed storylines,
new systems discovered, useful resources/equipment, and a high server reward.
The server token may contain a hidden verification goal; do not assume you know
it before play.

Track-specific play guidance:

- Start from player-visible observations and build your own model of the game.
- Prefer `list goals`, `list spells`, `list recipes`, `list areas`, and `list crit`
  over reading implementation or data files.
- If you cannot name the next unlock condition, observe more instead of grinding.
- Track both completed discoveries and dead ends; discovery quality matters here.

Verification:

At the end, call server-side `verify()` on the official game with no custom goal
unless you have independently inferred a better goal from player-visible state.
The token policy is authoritative.

Extra report fields:

- Most important discoveries.
- What you would try next if given another run.
