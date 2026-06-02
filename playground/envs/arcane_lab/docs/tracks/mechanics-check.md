---
id: playground.arcane_lab.tracks.mechanics-check
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Mechanics Check

Goal: demonstrate reliable understanding of core mechanics rather than pushing
the full prestige route. The official token target checks an early automation
and exploration route: complete `field_notes`, craft `focus_lens`, hire and use
a wizard assignment, and clear `shaded_grove` once.

Mechanics to exercise:

- Read structured observations correctly.
- Use `batch cast` and `batch transmute` when payloads do not conflict.
- Track action ticks and lifetime ticks.
- Manage mana around wizard automation instead of letting automation block a
  planned cast.
- Use buffs immediately before exploration and account for duration loss.
- Observe random crit rolls, but do not rely on a lucky roll to satisfy a stat
  gate.

Track-specific play guidance:

- Prefer short scripts under `logs\` that print each command, output, tick, and
  relevant stats.
- Stop and inspect after failed commands; repeated blind retries should be
  reported as a mechanics failure.
- This track should finish well before the hard budget. Obeying the soft stop is
  still scored, but a good run should not get close to it.

Verification:

At the end, call server-side `verify()` on the official game with no custom goal.
The token policy is authoritative.

Extra report fields:

- Batch commands used and why they were safe.
- Any failed command and the corrected mechanic.
- Whether the final route relied on random crits.
- Final soft stop status and soft stop score.
