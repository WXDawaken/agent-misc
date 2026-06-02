# Mail4Agent Feature Round 3 Eval

## Batch

- Results dir: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z`
- Objective analysis: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z\analysis.md`
- Large bridge replicate dir: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3_large_r2\20260323T131638Z`
- Large bridge combined objective analysis: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3_large_combined\analysis.md`
- Judge bundle: `E:\agent_misc\benchmarks\results\20260323T052945Z_judge_packets`
- Judged analysis: `E:\agent_misc\benchmarks\results\20260323T052945Z_judge_packets\judged_analysis.md`
- Large bridge `r2` judge bundle: `E:\agent_misc\benchmarks\results\20260323T133836Z_judge_packets`
- Large bridge `r2` judged analysis: `E:\agent_misc\benchmarks\results\20260323T133836Z_judge_packets\judged_analysis.md`
- Tasks:
  - `small_mail4agent_retry_queue_visibility`
  - `medium_mail4agent_thread_summary_and_unread_state`
  - `large_mail4agent_webhook_or_stdio_bridge_delivery`

## Config Note

- This batch still ran from the original `round3` feature seed, not the newer `round4` stabilized seed.
- The comparison itself is still internally pinned and fair on model plus reasoning effort: both modes recorded `resolved_model = gpt-5.4` and `resolved_reasoning_effort = xhigh`.
- Future reruns of these same task ids should prefer `E:\agent_misc\.tmp_test\mail4agent_feature_round4_20260323` plus the benchmark-scoped `E:\agent_misc\benchmarks\.codex_home`.

## Objective Readout

- All `6/6` runs passed objective validation.
- `single_xhigh` was faster on all `3/3` comparable task pairs.
- `single_xhigh` also used fewer total tokens on `small` and `large`.
- `subagents` used fewer total and fresh-input tokens on `medium`.

## Pair Highlights

- `small_mail4agent_retry_queue_visibility`
  - `single_xhigh`: `676.842s` adjusted, `2,363,977` total tokens
  - `subagents`: `745.689s`, `2,783,502` total tokens
- `medium_mail4agent_thread_summary_and_unread_state`
  - `single_xhigh`: `732.736s`, `3,984,887` total tokens
  - `subagents`: `782.261s` adjusted, `3,258,779` total tokens
- `large_mail4agent_webhook_or_stdio_bridge_delivery`
  - `single_xhigh`: `579.050s`, `1,859,585` total tokens
  - `subagents`: `796.074s`, `2,850,087` total tokens

## Judged Readout

- The first blinded judged-quality pass also favored `single_xhigh` overall.
- Pair preference went `2 : 1` for `single_xhigh`.
- Mean judged score favored `single_xhigh`, `4.167` vs `3.917`.
- Median judged score also favored `single_xhigh`, `4.250` vs `3.500`.
- Quality per minute and quality per 1k tokens both favored `single_xhigh`.

## Judged Task Split

- `large_mail4agent_webhook_or_stdio_bridge_delivery`
  - judged winner: `subagents`
  - score delta: `19` vs `14`
- `medium_mail4agent_thread_summary_and_unread_state`
  - judged winner: `single_xhigh`
  - score delta: `19` vs `14`
- `small_mail4agent_retry_queue_visibility`
  - judged winner: `single_xhigh`
  - score delta: `17` vs `14`

## Current Read

- This round points in the same direction as the first feature-extension batch: for these Python mailbox product-extension tasks, `single_xhigh` is currently the stronger default candidate overall.
- The one notable exception is the large bridge task, where judged preference favored `subagents` even though objective time and token usage favored `single_xhigh`.
- After adding a second objective replicate for the large bridge task, that objective split is now `2/2` in favor of `single_xhigh` on both adjusted wall time and total tokens.
- After adding a second blinded judged pass for the large bridge task, that judged split is now also `2/2` in favor of `subagents`.
- That means the remaining disagreement is no longer “objective is mixed”; it is now specifically “objective favors `single_xhigh`, while judged quality consistently favors `subagents` on the bridge task.”
- That makes the current policy read more nuanced than “single always wins”: for bridge-like large integration tasks, `subagents` may still buy higher judged quality even when it costs more time and tokens.
- This is still Codex single-rater evidence, not a human multi-rater study, so it should be treated as a strong working read rather than a final gold-standard verdict.
