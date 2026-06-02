# Arcane Lab Prompt Tracks

These tracks use the same server-backed game environment and mostly the same
official verification target, but vary how much strategic information the agent
receives in the prompt.

Prompt files are promptkit artifacts split into:

- `shared.md`: common workspace rules, SDK/server usage, auth-token safety,
  random crit expectations, budget rules, and shared report requirements.
- `<track>.md`: track-scoped goal, disclosure level, route hints, verification
  call, and extra report fields.
- `config.json`: track registry with prompt paths, workspace mode,
  `offline_practice`, default lifetime tick budgets, soft-stop gaps, token
  goals, reference policies, source-policy extras, and named suites.
- `draft-tool-building-axis.md`: draft-only analysis axis for helper-script /
  experiment-harness behavior. It is not part of the active track matrix.
- `warmup-mechanics-base.md` and `warmup-prestige-solve.md`: phase prompts for
  orchestration-only mechanics-warmup / prestige-solve fork studies.

Track runners render `shared.md` and the selected track through
`E:\agent_misc\promptkit`, then writes `.runner\prompt.vars.json`,
`.runner\prompt.shared.md`, `.runner\prompt.track.md`, `.runner\prompt.md`,
and lint output files for reproducibility.

Runner workspaces are prepared by `scripts\setup_agent_workspace.py`. The setup
script intentionally copies a lean player-facing slice instead of the whole
project: server implementation files, historical logs, saves, prior agent
workspaces, route-answer scripts, and prompt-track internals are omitted unless
a profile explicitly allows a file. Existing active tracks set
`offline_practice: true`, so their workspaces copy the direct local engine
(`game.py`, `data\`, and `sdk\`) plus allowed docs and agents can run offline
`ArcaneLabSDK` practice games. Future tracks can set `offline_practice: false`
to copy only the server-backed SDK files. Both modes still omit `server.py`,
`mcp_server.py`, runner scripts, historical logs, saves, prior agent
workspaces, and route-answer scripts.

Platform runners share the same preparation layer in
`scripts\runner_common.py` / `scripts\prepare_agent_run.py`; the individual
runner scripts keep only the platform-specific launch, monitoring, and summary
collection code. Run with OpenCode Go:

```powershell
.\scripts\run_opencode_go_playtest.ps1 -Model opencode-go/deepseek-v4-pro -Track budgeted-prestige
```

Run with official Claude Code after logging in or setting an Anthropic API key:

```powershell
.\scripts\run_claude_code_playtest.ps1 -Model opus -Effort high -Track budgeted-prestige
```

Use `-PromptPath <path>` only for custom one-off track-scoped prompts. If
omitted, the runner uses the selected track's `prompt_path` from
`docs\tracks\config.json` and combines it with the configured shared prompt.
Use `-SharedPromptPath <path>` only when deliberately testing a different shared
protocol. Use `-TickBudget <ticks>` to override the selected track's configured
hard budget for a one-off run.

Codex CLI can run a named suite directly. If neither `--track` nor `--suite` is
provided, it uses `default_suite` from `config.json`:

```powershell
python scripts\run_codex_cli_playtest.py --model gpt-5.4 --reasoning-effort high --suite core
python scripts\run_codex_cli_playtest.py --list-tracks
```

Use `scripts\prepare_agent_run.py track --offline-practice false` for a
one-off server-only workspace smoke. Normal runner scripts use each track's
configured `offline_practice` value.

Custom prompt paths may omit promptkit front matter, but adding `inputs` keeps
runner linting useful.

## Tracks

- `pure-blind`: no docs, helper scripts, source, data, or route notes. The agent
  must learn only from the prompt, SDK observations, player-visible list
  commands, and command outputs.
- `blind-discovery`: no explicit Echo Vault target in the prompt. The agent is
  asked to discover the game, push storylines, and verify against the token
  policy at the end. It may read the player-facing brief and SDK docs, but not
  scripts, source, data, or benchmark task notes.
- `visible-goal`: names `echo_vault_attuned` and `echo_anchor`, but does not
  give retire/insight thresholds or high-level route milestones.
- `mechanics-check`: early-route mechanics test for structured observations,
  batch commands, buff duration, automation mana interaction, random crit
  observation, and soft-stop compliance.
- `budgeted-prestige`: names the prestige target, lifetime budget discipline,
  checkpoint rules, and explicit final goal checks, but does not provide route
  milestones.
- `provided-helper-prestige`: same prestige target as `budgeted-prestige`, but
  includes a practice helper with route assertions so the agent does not need to
  rebuild common route-runner scaffolding or submit unclosed routes.
- `route-optimization`: gives high-level route milestones and asks the agent to
  execute the route efficiently under the lifetime budget.
- `crit-build-eval`: asks the agent to compare crit-investing and crit-neutral
  candidates in offline practice before spending one official random-crit
  prestige attempt.

## Suites

Suites are named track sets in `config.json`. They keep routine comparisons
cheap without deleting harder tracks:

- `smoke`: `mechanics-check`.
- `core`: `mechanics-check`, `route-optimization`, `budgeted-prestige`.
- `prestige`: `route-optimization`, `budgeted-prestige`, `crit-build-eval`.
- `helper-eval`: `provided-helper-prestige`.
- `discovery`: `pure-blind`, `blind-discovery`, `visible-goal`.
- `full`: every active single-run track in config order.
- `warmup`: one mechanics-check-style base session followed by independent
  prestige solve forks. This requires a runner that can create a base session
  and fork independent solve attempts.

## Budget Semantics

The official `tick_budget` is lifetime tick budget. Current run `tick` resets
after retirement; `lifetime_tick` does not. Tracks that mention a hard budget
tell the agent to use `observation["lifetime_tick"]`.

`per_run_tick_budget` is a separate optional constraint for specialized tasks.

Default runner budgets live in `config.json`:

| Track | Hard budget | Soft stop gap |
| --- | ---: | ---: |
| `mechanics-check` | 90 | 20 |
| `route-optimization` | 260 | 20 |
| `budgeted-prestige` | 260 | 20 |
| `provided-helper-prestige` | 260 | 20 |
| `warmup-fork-prestige` | 260 | 20 |
| `visible-goal` | 320 | 30 |
| `crit-build-eval` | 320 | 30 |
| `blind-discovery` | 360 | 30 |
| `pure-blind` | 420 | 40 |

## Soft Stop Scoring

The runner also mints a `soft_stop_tick`, computed as the hard budget minus the
track's configured `soft_stop_gap`, and the
server records it in `verification.json` as `softStopTick`. Crossing this line
does not make the official hard-budget verification fail, but it sets
`softStopExceeded=true`, records `softStopOverrun`, and gives `softStopScore=0`.
Runs that stop progression before the soft stop get `softStopScore=1`.

Soft stop is an advisory scoring line, not the hard cutoff. Agents should avoid
speculative progression after it, but a short known sequence that completes the
official goal can still be worth taking under the hard budget. Such runs remain
hard-budget accepted but receive the appropriate soft-stop score.

## Verification Outcome

`accepted` means the official server verification accepted the run under the
hard budget and token policy. It does not by itself mean every goal subcheck
passed. Verification also reports:

- `goalAchieved`: `true`, `false`, or `null` when no goal was scored.
- `goalCompletion`: passed/total counts plus failed goal keys.
- `outcome`: `success` for accepted plus all goals achieved, `partial` for
  accepted with failed goal keys, `rejected` for hard-budget/token rejection,
  and `accepted` when no explicit goal was scored.

## Route Quality

Runner summaries include `route_quality` as an auxiliary comparison score. It
combines goal completion, lifetime tick efficiency, soft-stop score,
failed-command cleanliness, source-policy compliance, and retirement target
completion. It also records route signals such as command count, retirement
ticks, post-retire ticks, and random crit roll counts.

`route_quality` is not the official verifier. Treat it as a sorting and review
aid: official success still comes from server verification, while route quality
helps identify routes that are slower, messier, source-leaky, or potentially
helped by random crits.

## Provided Helpers

`provided-helper-prestige` includes `tools\arcane_practice_helper.py` in the
agent workspace. This helper was extracted from successful GPT-style practice
tooling and then stripped down so it does not contain route commands, route
search, hidden thresholds, or recommendations. It runs agent-provided route
files under `logs\`, prints compact state summaries, saves direct practice
state under `logs\`, and can execute/verify the official server game.

Route files can include zero-tick helper directives:

```text
checkpoint after_gear
expect area gear_sanctum clears >= 1
expect resources.paper >= 16
expect buff route_sketch active
expect recipe astral_array known
expect recipe echo_anchor owned
expect goal achieved
```

Inline assertions are also available through repeated `--expect` flags, and
`--json-out logs\helper_summary.json` writes a machine-readable final state,
failure list, assertion list, and verification result. Failed commands or failed
assertions mean the route is not proven.

Use this track to measure whether models that repeatedly rebuild similar helper
scripts improve when the scaffolding burden is removed. Compare it against
`budgeted-prestige`; do not mix the two as identical baselines.

## Warmup Fork Tracks

Warmup fork tracks are meta-tracks for measuring how much a model benefits from
shared exploration context before independent solve attempts. They are declared
in `config.json`, but they are not normal single-session tracks. The standard
Codex/OpenCode/Claude runner path should reject them until a warmup/fork
orchestrator is used.

The active warmup track is `warmup-fork-prestige`: one mechanics-check-style
base session, then five independent prestige solve attempts forked from that
same base by default. The base is deliberately not a route-search rollout; it
tests whether shared mechanics memory improves later solves without seeding a
specific prestige route.

Warmup base sessions should not create official server games. They use offline
practice and write only compact mechanics artifacts:

- `logs\mechanics.md`
- `logs\gotchas.md`
- `logs\warmup_summary.md`

Forked solve attempts may read those warmup artifacts but should treat them as
evidence, not truth. Each fork must build and verify its own prestige route,
write `logs\fork_review.md`, produce its own `logs\final_route.md`, and spend
exactly one official server game.

For OpenCode-style orchestration, the intended shape is:

```powershell
opencode run "<warmup prompt>"
opencode run --session <warmup_session_id> --fork "<solve prompt>"
opencode run --session <warmup_session_id> --fork "<solve prompt>"
```

Use `--fork` for every solve attempt. Continuing the same session without
forking turns the sample into sequential self-repair rather than independent
solve attempts from the same warmup base.

## Reference Compliance

Each track has a reference policy rendered into the shared prompt. The runner
also scans OpenCode tool inputs after the run and writes `source_policy` into
`.runner\summary.json` with any detected source, data, helper-script, debug-goal,
or track-specific docs violations.
