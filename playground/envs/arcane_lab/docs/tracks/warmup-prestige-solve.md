---
id: playground.arcane_lab.tracks.warmup-prestige-solve
engine: mini-mustache
inputs:
  TRACK: string
  HANDOFF_MODE: string
  HANDOFF_CONTEXT_POLICY: string
---
Track phase: `{{TRACK}}` / Warmup Handoff Prestige Solve

Goal: use the allowed warmup handoff to complete the prestige Echo Vault
target in one official server-backed attempt while staying under the lifetime
tick budget.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

Warmup context handling:

Handoff mode: `{{HANDOFF_MODE}}`

{{HANDOFF_CONTEXT_POLICY}}

- Start by reading the warmup artifacts if present:
  - `logs\mechanics.md`
  - `logs\gotchas.md`
  - `logs\warmup_summary.md`
- The warmup base is mechanics memory, not a route handoff. Do not expect it to
  contain a recommended prestige route or late-game route candidates.
- Treat warmup notes as evidence, not truth. Re-verify any assumption that can
  break the official route: batch safety, resource counts, buff duration, boss
  counters, retirement insight, and random-crit-dependent thresholds.
- Write `logs\fork_review.md` before official play. Keep it short:
  - mechanics notes accepted,
  - assumptions re-tested,
  - assumptions invalidated or repaired,
  - warmup bias or missing-mechanics risk,
  - final risk level.
- Do not read sibling solve outputs. A solve attempt may use only the allowed
  handoff for its mode, not the transcripts or files from other solve attempts.

Track-specific play guidance:

- You may also read `docs\tasks.md` for benchmark-style task context.
- Use offline practice to build and repair your own route under a fresh local
  practice game. The warmup should help you avoid rediscovering command and
  observation mechanics; it should not substitute for proving the prestige
  route.
- Before creating the official server game, prove a complete end-to-end route
  from a new game through `echo_vault_attuned` and `echo_anchor`; do not spend
  the official new game on a partial mid-route milestone.
- Before calling `ArcaneLabServerSDK(new=True)`, write `logs\final_route.md`.
  Keep it compact and make it the source of truth for the official attempt.
  It must include:
  - ordered command blocks for the official run,
  - expected lifetime tick checkpoints for Training/Shaded, Sunken, Gear,
    Prism, Living/Astral, retirement, and Echo,
  - required stats, buffs, equipment, and counters for boss gates,
  - exact stop or pivot conditions if a checkpoint slips.
- `logs\final_route.md` is not valid if any required late route is marked
  `TBD`, `discover after`, or otherwise left to official exploration.
- During official play, update only a small `logs\official_status.md` with
  current checkpoint deltas. If the official state diverges from
  `logs\final_route.md`, compare against the route plan and avoid ad hoc
  grinding.
- After the official game starts, do not run tick-spending diagnostic scripts to
  test unknown requirements, unknown buffs, or possible boss counters. Only use
  zero-tick observations such as `observe()`, `status`, `list areas`, `list
  spells`, `list recipes`, `list buffs`, and `list goals` to diagnose a
  divergence.
- If the inherited warmup context appears biased by an overfit or invalid
  mechanics note, name the poisoned assumption in `logs\fork_review.md`, repair
  only that mechanics dependency, and prove the affected route segment again.
- If you reach the soft-stop line with only a known final target action left
  (for example crafting `echo_anchor`), finish the target while staying under
  the hard budget and report the soft-stop tradeoff.
- At or after the soft stop, continue only when the remaining command sequence
  from the current checkpoint to the final target fits the hard budget.
  Otherwise stop immediately, call `verify()` for the partial official result,
  and report the first missing gate.

Before the final report, explicitly evaluate:

- `echo_vault_attuned` completed?
- `echo_anchor` owned?
- `echo_vault` unlocked and cleared?
- retirements >= 1?
- insight >= 12?
- run >= 2?
- Did the warmup base help, hurt, or bias the solve attempt?

Do not describe the run as successful unless `echo_vault_attuned` is complete
and `echo_anchor` is owned.

Verification:

At the end, call server-side `verify()` on the official game with this goal:

```python
{
    "storyline": "echo_vault_attuned",
    "recipe": "echo_anchor",
    "area": "echo_vault",
    "area_clears": 1,
    "retirements": 1,
    "insight": 12,
    "run": 2
}
```

Extra report fields:

- Whether `echo_vault_attuned` and `echo_anchor` were achieved.
- Which warmup artifacts were used.
- Which warmup assumptions were invalidated or repaired.
- Whether this solve attempt benefited from mechanics memory, suffered warmup
  bias, or behaved like a cold solve.
