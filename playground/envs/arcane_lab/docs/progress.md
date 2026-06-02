# Arcane Lab Progress

Last updated: `2026-05-16`

## Current State

- `Arcane Lab` is the original text RPG / incremental mimic environment.
- It remains the default environment for root compatibility shims: root `game.py`, `mcp_server.py`, and `sdk\` point at Arcane-facing behavior.
- The active benchmark direction is official token-gated play through isolated agent workspaces, promptkit-rendered track prompts, server verification, source-policy scanning, route-quality summaries, and replay overlays.

## Surface

- Engine/data: `envs\arcane_lab\game.py`, `envs\arcane_lab\data\arcane_lab.json`.
- SDKs: `envs\arcane_lab\sdk\arcane_lab_sdk.py`, `envs\arcane_lab\sdk\server_sdk.py`, `envs\arcane_lab\sdk\result.py`.
- Server/replay: `envs\arcane_lab\server.py`, `envs\arcane_lab\static\replay.html`.
- MCP: `envs\arcane_lab\mcp_server.py`.
- Agent docs: `README.md`, `docs\agent-brief.md`, `docs\sdk-api.md`, `docs\tasks.md`, `docs\design.md`.
- Track prompts/config: `docs\tracks\shared.md`, track-specific prompts, `docs\tracks\config.json`.
- Helper surface: `tools\arcane_practice_helper.py` for provided-helper prestige tracks.

## Mechanics

- Manual `study`, `cast`, `explore`, `transmute`, and `hire` each consume one game tick; automation can overlap with action ticks.
- `batch cast` and `batch transmute` spend one action tick, resolve payloads by explicit `@priority` then order, and reject duplicate payload ids.
- Track scoring uses lifetime tick budgets by default; per-run tick budgets are optional and only for tracks that intentionally need that shape.
- Soft stops are advisory scoring signals, not hard rejection gates.
- Server tokens are authoritative for environment id, track id, official budget, soft stop, crit mode, base crit parameters, and max-new-game policy.
- Crit modes are deterministic `charge` and server-seeded `random`. Base charge bonus, random chance, and random bonus are track-configurable and runner-rendered.
- `keen_focus` is mode-adaptive. In random crit mode it multiplies effective crit chance; `seer_glass` is the first crit-chance equipment item.
- Retirement preserves completed storylines, permanent bonuses, discovered areas/elements, and insight; it resets current-run resources, gear, clears, and element levels.
- Prestige route content exists through `echoed_foundation`, `echo_vault`, `echo_vault_attuned`, and `echo_anchor`.
- Equipment enhancement uses spare copies and exponential costs.
- Boss pressure uses soft counters rather than hard counters.
- Game help exposes `list reference` for planning references, buff durations, batch priority semantics, and route discipline without revealing locked spell details.

## Tracks

- Active single-run tracks: `mechanics-check`, `route-optimization`, `budgeted-prestige`, `provided-helper-prestige`, `visible-goal`, `blind-discovery`, `pure-blind`, and `crit-build-eval`.
- `default_suite` is `core`: `mechanics-check`, `route-optimization`, `budgeted-prestige`.
- Other named suites include `smoke`, `prestige`, `helper-eval`, `discovery`, and `full`.
- `warmup-fork-prestige` is orchestration-only: mechanics-check-style base plus prestige solve forks. Normal single-session runners intentionally reject it.
- `provided-helper-prestige` ships `tools\arcane_practice_helper.py`. The helper supports route replay, `checkpoint` and `expect` directives, goal verification, and `--json-out`.
- `budgeted-prestige` requires a compact `logs\final_route.md` before official play and discourages official-budget diagnostics.
- `crit-build-eval` is the random-crit comparison track. Current server-backed random crit settings are base chance `18%` and random attack bonus `+50%`.

## Runner And Harness Notes

- Agent workspaces are generated through `scripts\setup_agent_workspace.py`.
- Codex CLI, OpenCode Go/direct, Claude Code DeepSeek, and official Claude Code runners share `scripts\runner_common.py`.
- Prompt rendering uses root `promptkit`.
- Source-policy scanning treats forbidden engine/source files as exact path components.
- Runner summaries include `route_quality`, soft-stop compliance, failed-command cleanliness, source-policy compliance, retirement target completion, and random-crit occurrence signals.
- Replay UI loads persisted `verification.json` and visualizes route quality, soft-stop and hard-budget lines, retire markers, failed commands, and crit roll/hit markers.
- OpenCode warmup runner supports `session-fork`, `artifact-only`, and `cold-solve` handoff modes.
- Claude Code DeepSeek runner uses stdin prompt delivery, stream-json verbose output, noninteractive track permissions, and `Edit`/`MultiEdit` for helper repair while blocking web/notebook tools.

## Verification Baseline

- Compile/smoke set:
  - `python -m py_compile game.py server.py server_core.py mcp_server.py sdk\arcane_lab_sdk.py sdk\server_sdk.py sdk\result.py envs\arcane_lab\game.py envs\arcane_lab\server.py envs\arcane_lab\mcp_server.py envs\arcane_lab\sdk\arcane_lab_sdk.py envs\arcane_lab\sdk\server_sdk.py envs\arcane_lab\sdk\result.py scripts\verify.py`
  - `python game.py --new --script scripts\smoke.txt --no-save`
  - `python game.py --new --script scripts\midgame_smoke.txt --no-save`
  - `python game.py --new --script scripts\late_playtest.txt --no-save`
  - `python game.py --new --script scripts\retire_smoke.txt --no-save`
  - `python game.py --new --script scripts\prestige_smoke.txt --no-save`
  - `python scripts\server_smoke.py`
  - `python scripts\server_sdk_smoke.py`
  - `python scripts\crit_smoke.py`
  - `python scripts\tick_budget_smoke.py`
- Track validation:
  - `python -m json.tool envs\arcane_lab\docs\tracks\config.json`
  - promptkit lint/render through `scripts\prepare_agent_run.py`.
  - PowerShell AST parse for runner `.ps1` scripts.

## Reference Results

- Midgame smoke: `living_formula` / `prism_observatory` succeeds around tick `75` under budget `85`.
- Late smoke: `astral_capstone` / `astral_foundry` succeeds around lifetime tick `216`; budget `215` is expected to fail only on budget.
- Prestige smoke: `echo_vault_attuned` plus `echo_anchor` succeeds at lifetime tick `222`; budget `220` is expected to fail, `222` passes.

## Benchmark Conclusions

- `budgeted-prestige` remains the main discriminator: it separates route-harness quality, soft-stop interpretation, retirement planning, and official-run discipline.
- Strong GPT-series samples:
  - Codex CLI `gpt-5.4` high repeatedly succeeds, with representative full routes around `166-189` lifetime ticks.
  - Codex CLI `gpt-5.5` high/xhigh succeeds reliably under current docs, with representative routes around `125` ticks.
  - OpenCode OAuth `openai/gpt-5.5` xhigh produced the strongest current GPT-series prestige route: `94/260` lifetime ticks, `S` route quality, one retirement, and seed replay success.
  - OpenCode OAuth `openai/gpt-5.4` high produced strong success samples around `98` and `120` ticks.
- OpenCode `openai/gpt-5.2` can solve short mechanics and discovered a valid `164` tick prestige route offline, but did not self-submit the official server run in the sampled budgeted-prestige attempt.
- DeepSeek v4-pro can solve prestige when the prompt/harness constrains route closure well, especially with assertive helper support or warmup/fork handoff. Its main weakness is broad route exploration and late route-compression drift.
- MiMo, Kimi, GLM, Qwen, and MiniMax show partial progress bands but weaker route reuse, helper discipline, or official-run closure than the stronger GPT/DeepSeek samples.
- Warmup/fork handoff helps DeepSeek substantially. `session-fork` is strongest; `artifact-only` still helps but is less stable. Mimo did not benefit enough from warmup/fork in the recorded sample.

## External Model Notes

- DeepSeek v4-pro through Claude Code completed independent prestige and random-crit prestige playtests successfully after harness fixes.
- Claude Code DeepSeek harness differences mattered: Windows argv limits, stream-json verbosity, noninteractive permissions, and allowing edit tools all affected whether a run could fairly exercise the model.
- OpenCode Go random-crit matrix: DeepSeek v4-pro succeeded; Qwen, MiniMax, and Mimo made partial prestige progress; Kimi and GLM failed/rejected on budget or insufficient prestige state.
- Historical detailed run narratives remain in per-run reports under `agent_workspaces\` and official `logs\server\games\<game_id>\verification.json`.

## Next

- Keep detailed run-by-run narratives out of the root playground progress file.
- Use this file for durable Arcane mechanics, track semantics, runner conclusions, and benchmark readouts.
- Add source-policy overlays to replay artifacts when inspecting agent workspaces.
- Use suites consistently in non-Codex matrix orchestration.
- Keep refining bounded route-file/helper discipline for long prestige tracks.
