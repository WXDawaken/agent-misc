# DeepSeek and Codex Single-File Eval Notes

Date: 2026-04-24

## Scope

The first runs compare ordinary single-file coding behavior. A later section
adds a small coding-agent repair task that requires reading files, running
tests, editing code, and rerunning tests.

Generation modes:

- DeepSeek runs use the OpenAI-compatible `chat/completions` API.
- Codex runs use `codex exec` and then local tests against the emitted
  `solution.py`.
- Claude Code DeepSeek retests use DeepSeek's Anthropic-compatible endpoint.
- All tasks are judged by deterministic local Python tests.

## Models

| Label | Runner | Model | Reasoning |
|---|---|---|---|
| DS-V4-Pro | DeepSeek API | `deepseek-v4-pro` | `thinking=enabled`, `reasoning_effort=high` |
| DS-V4-Flash | DeepSeek API | `deepseek-v4-flash` | `thinking=enabled`, `reasoning_effort=max` |
| GPT-5.4 | Codex CLI | `gpt-5.4` | `high` |
| GPT-5.3 Codex Spark | Codex CLI | `gpt-5.3-codex-spark` | `high` |

## Algorithm and Data-Structure Generation

Twelve tasks: LRU cache, shortest subarray at least K, weighted interval
scheduling, Tarjan bridges, 2D rain water, regex DP, strange printer, smallest
sufficient team, tree rerooting distances, count-smaller-after-self, maximal
rectangle, and JSON Merge Patch.

| Model | Pass | Total Time | Avg / Task | Slowest | Notes |
|---|---:|---:|---:|---:|---|
| DS-V4-Pro | 12/12 | 520.5s | 43.4s | 147.4s | Correct, but long-tail latency is large. |
| DS-V4-Flash | 12/12 | 381.1s | 31.8s | 85.5s | Correct and faster than Pro, but sometimes uses many thinking tokens. |
| GPT-5.4 | 12/12 | 236.3s | 19.7s | 27.8s | Correct and fairly stable. |
| GPT-5.3 Codex Spark | 12/12 | 111.2s | 9.3s | 10.3s | Correct, fastest, and most stable on this suite. |

## Single-File Bugfix

Four tasks: CSV aggregation, topological scheduler, sliding-window rate limiter,
and JSON Pointer set semantics.

| Model | Pass | Total Time | Avg / Task | Slowest | Notes |
|---|---:|---:|---:|---:|---|
| DS-V4-Pro | 4/4 | 274.5s | 68.6s | 136.7s | Correct, but slow on semantic edge-case repair. |
| DS-V4-Flash | 4/4 | 154.3s | 38.6s | 84.8s | Correct, faster than Pro with a visible JSON Pointer long tail. |
| GPT-5.4 | 4/4 | 100.5s | 25.1s | 33.8s | Correct and stable. |
| GPT-5.3 Codex Spark | 4/4 | 45.3s | 11.3s | 16.4s | Correct and fastest again. |

## Current Quality Read

On these small and medium single-file tasks, quality is tied by pass rate.
Generated code inspection did not show an obvious correctness-quality gap:
all models produced standard solutions for the algorithm tasks and acceptable
fixes for the bugfix tasks.

The main observed separator so far is operational:

- GPT-5.3 Codex Spark is the fastest and has the tightest latency range.
- GPT-5.4 is slower than Spark but still much steadier than DeepSeek.
- DeepSeek V4 Flash is faster than Pro but can still spend heavily on thinking.
- DeepSeek V4 Pro is correct but has the largest latency tail in these runs.

## Robustness Suite

Four tasks: range add/range sum with a large-input performance check, edit
distance with randomized oracle checks, min-window substring with randomized
oracle checks, and half-open interval union with randomized oracle checks.

| Model | Pass | Total Time | Avg / Task | Slowest | Notes |
|---|---:|---:|---:|---:|---|
| DS-V4-Pro | 4/4 | 270.3s | 67.6s | 133.6s | Correct, but min-window produced a large thinking tail. |
| DS-V4-Flash | 4/4 | 100.5s | 25.1s | 48.3s | Correct and substantially faster than Pro on this suite. |
| GPT-5.4 | 4/4 | 64.9s | 16.2s | 23.5s | Correct and stable. |
| GPT-5.3 Codex Spark | 4/4 | 37.4s | 9.4s | 10.6s | Correct and again the fastest/steadiest run. |

Robustness result paths:

- Spark: `E:\agent_misc\deepseek_single_file_eval\codex_cli_runs\20260424-133925`
- GPT-5.4: `E:\agent_misc\deepseek_single_file_eval\codex_cli_runs\20260424-134124`
- DS-V4-Flash: `E:\agent_misc\deepseek_single_file_eval\runs\20260424-133925`
- DS-V4-Pro: `E:\agent_misc\deepseek_single_file_eval\runs\20260424-134124`

## Updated Read

Randomized oracle tests and one performance trap still did not separate these
models by pass/fail on this task size. The quality read remains that all four
are strong for small and medium single-file work. The clearest differentiator is
latency stability, where Spark is consistently best, GPT-5.4 second, Flash
third, and Pro last.

## Agent Repair Smoke Test

Fixture: `E:\agent_misc\deepseek_single_file_eval\agent_eval`.

Task shape: a tiny Python project with `src/inventory.py`, pytest tests, and
five visible failures. The agent had to run tests, inspect source/tests, edit
the implementation, and rerun `python -m pytest -q`. The visible failures cover
quoted CSV commas, transactional negative-stock rejection, inclusive low-stock
thresholds, and sorted report output.

Runner notes:

- Codex CLI runs used `--dangerously-bypass-approvals-and-sandbox` inside
  isolated copied fixture directories because this CLI build ignored
  `-s workspace-write` and otherwise fell back to read-only.
- OpenCode DeepSeek runs used `--dangerously-skip-permissions`.
- `deepseek-v4-flash` was added to the local OpenCode DeepSeek provider config
  so it can be selected as `deepseek/deepseek-v4-flash`.
- Agent wall times were observed from terminal sessions, not a dedicated timing
  harness.

| Model / Runner | Visible Tests | Iteration Behavior | Holdout: cumulative same-item negative | Holdout: whitespace-only CSV row | Quality Read |
|---|---:|---|---|---|---|
| GPT-5.3 Codex Spark high / Codex CLI | 5/5 | Ran tests, patched once, reran green. | Pass | Pass | Best patch in this fixture. |
| GPT-5.4 high / Codex CLI | 5/5 | Ran tests, patched once, reran green. | Pass | Fail: `ValueError` on one-cell blank row. | Good visible repair, one parser edge miss. |
| DS-V4-Pro max / OpenCode | 5/5 | Ran tests, patched, saw 2 failures, patched again, reran green. | Fail: no raise, stock becomes `-1`. | Fail: `IndexError` on one-cell blank row. | Agent loop works with more time, but patch overfit visible tests. |
| DS-V4-Flash max / OpenCode | 5/5 | Ran tests, wrote implementation patch, reran green. | Pass | Pass | Strongest DeepSeek agent result here; cleaner than Pro. |

Agent result paths:

- Spark: `E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\20260424-164942\codex_spark_high_bypass`
- GPT-5.4: `E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\20260424-164942\codex_gpt54_high_bypass`
- DS-V4-Pro: `E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\20260424-164942\opencode_deepseek_v4_pro`
- DS-V4-Flash: `E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\20260424-164942\opencode_deepseek_v4_flash`

Agent read: the OpenCode/DeepSeek integration is usable when permissions are
skipped and the model is given enough time. The key separator shifted from
"can it operate tools" to "does the patch generalize beyond visible tests".
On this one repair task, V4 Flash was better than V4 Pro.

## Multi-File Agent Repair Test

Fixture: `E:\agent_misc\deepseek_single_file_eval\agent_eval\multifile_template`.

Task shape: a tiny checkout service split across `catalog.py`,
`checkout.py`, and `promotions.py`. The visible suite starts at 4 failures and
1 pass. The agent must fix SKU normalization, catalog lookup, cart aggregation,
quantity validation, coupon normalization, shipping threshold logic, tax
rounding, and the promotion math.

Run directory: `E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\multi-20260424-170520`.

| Model / Runner | Visible Tests | Hidden Checks | Iteration Behavior | Quality Read |
|---|---:|---:|---|---|
| GPT-5.4 high / Codex CLI | 5/5 | 3/3 | Patched all three modules, reran tests, fixed promotion math on second pass. | Best result in this multi-file test. |
| GPT-5.3 Codex Spark high / Codex CLI | 5/5 | 2/3 | Patched all three modules and got green, but inferred an 18% clearance discount. | Fast and agentic, but overfit a visible numeric expectation. |
| DS-V4-Pro max / OpenCode | 4/5 | 1/3 | Fixed navigation/cart/shipping pieces, then stalled on promotion math and hit an OpenCode/DeepSeek thinking-mode error. | Tool loop works, but did not complete; left `debug_test.py`. |
| DS-V4-Flash max / OpenCode | 4/5 | 1/3 | Fixed navigation/cart/shipping pieces, then looped on promotion math for several minutes and was stopped. | Similar to Pro here; no API error, but no final repair. |

Hidden checks:

- Multi-space SKU normalization: `"  clearance   tin  "` must become
  `CLEARANCE-TIN`.
- Clearance-only discount: a `5500` cent clearance line should get a `1100`
  cent category discount.
- Shipping threshold after discount: `5600 - LESS1000` should still charge
  shipping.

Multi-file read: on this harder agent task, the DeepSeek/OpenCode integration
was able to read files, run tests, edit multiple files, and iterate, but both
DeepSeek variants failed to infer the final business rule from the tests.
GPT-5.4 produced the most semantically correct patch. Spark remained fast and
effective, but it showed a concrete visible-test overfit.

## Claude Code DeepSeek Retest

Reference setup:

- DeepSeek coding-agents guide:
  `https://api-docs.deepseek.com/guides/coding_agents`
- DeepSeek Anthropic API guide:
  `https://api-docs.deepseek.com/guides/anthropic_api`
- Installed Claude Code version: `2.1.119`.
- Endpoint: `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`.
- Main model selection was direct:
  `--model deepseek-v4-pro` and `--model deepseek-v4-flash`.
- The Opus/Sonnet/Haiku environment variables are default/fallback mappings for
  Claude Code's internal model-family slots. They were not needed to select the
  tested models in these runs.

Run directory:
`E:\agent_misc\deepseek_single_file_eval\agent_eval\runs\claude-20260424-173812`.

Single-file inventory fixture:

| Model / Runner | Visible Tests | Hidden Checks | Iteration Behavior | Quality Read |
|---|---:|---:|---|---|
| DS-V4-Pro max / Claude Code | 5/5 | 2/2 | Completed and reran visible tests green. | Best DeepSeek result on this single-file agent fixture. |
| DS-V4-Flash max / Claude Code | 5/5 | 1/2 | Completed and reran visible tests green. | Visible repair passed, but missed cumulative same-item negative-stock rollback. |

Multi-file checkout fixture:

| Model / Runner | Visible Tests | Hidden Checks | Iteration Behavior | Quality Read |
|---|---:|---:|---|---|
| DS-V4-Pro max / Claude Code | 4/5 | 1/3 | Modified the project but ran too long with no final output; process was stopped before completion. | Claude Code avoided the earlier OpenCode `reasoning_content` error, but Pro still failed to finish this task. |
| DS-V4-Pro high / Claude Code | 5/5 | 0/3 | Completed after about 5.5 minutes and reran visible tests green. | Better operational completion than `max`, but worse hidden quality: multi-space SKU was not collapsed, clearance stayed at 10%, and `LESS1000` was inferred as a per-unit discount. |
| DS-V4-Flash max / Claude Code | 5/5 | 1/3 | Completed cleanly and reran visible tests green. | Better operational fit than OpenCode Flash here, but still overfit the visible 18% discount and missed multi-space SKU normalization. |

Claude Code read: direct DeepSeek model names work. For basic single-file agent
repair, Claude Code plus DS-V4-Pro produced a stronger DeepSeek result than the
OpenCode Pro run. For the harder multi-file task, Claude Code improved Flash's
visible completion behavior, but hidden tests still show the same underlying
quality issue: visible green does not reliably imply semantic generalization.
Pro remained operationally slow on the multi-file task even with extra runtime;
lowering Pro from `max` to `high` let the run finish, but produced a more
overfit patch on this fixture.

## Next Test Ideas

The next suite should move beyond single-file generation if more separation is
needed.

Possible next tasks:

| Task | Target Risk |
|---|---|
| Larger multi-file patch from failing tests | Tests repo-local navigation and change scoping beyond a one-file fix. |
| Code review with seeded bugs | Measures recall, false positives, and severity ordering. |
| Long-context bug localization | Measures retrieval and attention under noise. |
| Multi-turn repair | Measures whether the model can use a failing test to correct its own first attempt. |
