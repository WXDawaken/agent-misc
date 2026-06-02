---
id: playground.arcane_lab.tracks.provided-helper-prestige
engine: mini-mustache
inputs:
  TRACK: string
---
Track: `{{TRACK}}` / Provided Helper Prestige

Goal: complete the same prestige Echo Vault target as `budgeted-prestige`, but
use the provided thin helper to avoid repeatedly rebuilding the same practice
script scaffolding.

Target outcomes, best first:

- Complete `echo_vault_attuned`.
- Craft `echo_anchor`.
- If that is too hard, reach run 2 after retirement and unlock `echo_vault`.

Provided helper:

- You may use `tools\arcane_practice_helper.py`.
- Helper positioning: this is benchmark scaffolding for route verification, not
  an in-game mechanic, not a source of hidden strategy, and not an autoplayer.
- The helper is a thin command runner, summarizer, and route assertion checker
  extracted from successful GPT-style practice tooling. It does not contain a
  route or route search policy.
- Do not edit the helper. Write your candidate route files under `logs\`, then
  run them through the helper.
- For direct practice, run the helper in new-game mode with a `logs\` command
  file and a `logs\` state file.
- For official execution after `logs\final_route.md` is ready, run the helper in
  server new-game mode with `logs\official_commands.txt` and verification
  enabled.
- Route files may include zero-tick helper directives:
  - `checkpoint after_gear`
  - `expect area gear_sanctum clears >= 1`
  - `expect resources.paper >= 16`
  - `expect buff route_sketch active`
  - `expect recipe astral_array known`
  - `expect recipe echo_anchor owned`
  - `expect goal achieved`
- Prefer running candidate routes with `--fail-exit --json-out
  logs\helper_summary.json`; a route with failed commands or failed `expect`
  checks is not proven.

Track-specific play guidance:

- You may also read `docs\tasks.md` for benchmark-style task context.
- Maintain two concise working notes while practicing:
  - `logs\mechanics.md`: verified mechanics only. Include short evidence such
    as command output, checkpoint name, or tick/state. Mark guesses as
    `unverified`, and mark disproven assumptions as `invalidated`.
  - `logs\progress.md`: current best route, checkpoint ticks/resources, known
    blockers, budget delta, and the next bounded experiment.
- Keep these notes short and current. They are working memory for route
  compression, not a separate scoring target. Before official play, derive
  `logs\final_route.md` and `logs\official_commands.txt` from the current notes,
  then prove the route with a fresh helper replay; the notes themselves are not
  proof.
- Before creating the official server game, use offline practice to prove a
  complete end-to-end route from a new game through `echo_vault_attuned` and
  `echo_anchor`; do not spend the official new game on a partial mid-route
  milestone.
- Keep offline practice bounded. Use the helper to run compact candidate route
  files with checkpoints and `expect` assertions, not open-ended loops. Once a
  candidate route reaches all target outcomes under the hard budget and all
  assertions pass, stop broad exploration.
- Before calling `ArcaneLabServerSDK(new=True)` or running the helper in server
  new-game mode, write `logs\final_route.md`. Keep it compact and make it the
  source of truth for the official attempt. It must include:
  - ordered command blocks for the official run,
  - expected lifetime tick checkpoints for Training/Shaded, Sunken, Gear,
    Prism, Living/Astral, retirement, and Echo,
  - required stats, buffs, equipment, and counters for boss gates,
  - exact stop or pivot conditions if a checkpoint slips.
- Also write `logs\official_commands.txt` as the command-only sequence to feed
  to the helper for the official attempt.
- Keep a checked copy of the same route under `logs\` with helper `expect`
  directives. It should prove resource counts, buffs, equipment ownership, area
  clears, retirement state, and final goal completion before official play.
- `logs\final_route.md` is not valid if any required late route is marked
  `TBD`, `discover after`, or otherwise left to official exploration. It must
  name the exact Astral Foundry, retirement, Echo Vault, and `echo_anchor`
  command blocks before the official game starts.
- Do not start the official run unless `logs\final_route.md` leaves a safety
  margin under the hard budget and names the post-retirement Echo commands. If
  offline practice cannot reach the full target, report that and preserve the
  official attempt instead of converting it into exploration.
- If the proven route misses only the soft-stop line but still reaches all
  target outcomes under the hard budget, prefer running the official route over
  unbounded optimization. Report the soft-stop tradeoff and any single known
  optimization opportunity.
- At every 25 lifetime ticks, checkpoint whether your next commands directly
  advance the prestige goal.
- If you cannot name the missing unlock condition, observe with `list goals`,
  `list areas`, `list spells`, and `list recipes` instead of grinding.
- During official play, update only a small `logs\official_status.md` with
  current checkpoint deltas. If the official state diverges from
  `logs\final_route.md`, compare against the route plan and avoid ad hoc
  grinding.
- After the official game starts, do not run tick-spending diagnostic scripts to
  test unknown requirements, unknown buffs, or possible boss counters. Only use
  zero-tick observations such as `observe()`, `status`, `list areas`, `list
  spells`, `list recipes`, `list buffs`, and `list goals` to diagnose a
  divergence.
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
- Did the provided helper reduce or distort your offline practice process?

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
- Checkpoint decisions, especially whether/when to retire.
- Whether `tools\arcane_practice_helper.py` helped, confused, or constrained
  your practice.
