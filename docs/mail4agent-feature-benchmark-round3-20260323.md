# Mail4Agent Feature Benchmark Round 3

## Goal

Launch a third Python feature-extension batch for `mail4agent` using the explicit-config benchmark harness and the current prompt policy that keeps `single_xhigh` in a single thread with an explicit "do not spawn or use subagents" instruction.

## Selected Tasks

- `small_mail4agent_retry_queue_visibility`
- `medium_mail4agent_thread_summary_and_unread_state`
- `large_mail4agent_webhook_or_stdio_bridge_delivery`

## Seed Workspace

- `E:\agent_misc\.tmp_test\mail4agent_feature_round3_20260323`

## Current Run

- Results root: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z`
- Live dashboard: `http://127.0.0.1:8026`
- Current state: `completed`
- Current run id: `none`

## Objective Readout

- All `6/6` runs passed objective validation.
- `single_xhigh` was faster on all `3/3` comparable task pairs.
- `single_xhigh` also used fewer total tokens on `small` and `large`.
- `subagents` used fewer total and fresh-input tokens on `medium`.
- Formal batch analysis now lives at `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z\analysis.md`.

## Judged Readout

- Blind packet bundle: `E:\agent_misc\benchmarks\results\20260323T052945Z_judge_packets`
- Deblinded judged analysis: `E:\agent_misc\benchmarks\results\20260323T052945Z_judge_packets\judged_analysis.md`
- Pair preference favored `single_xhigh` `2 : 1`.
- The one judged exception was `large_mail4agent_webhook_or_stdio_bridge_delivery`, where `subagents` was preferred despite losing on objective time and tokens.

## Large Bridge Replicate

- Follow-on results dir: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3_large_r2\20260323T131638Z`
- Combined large-task objective analysis: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3_large_combined\analysis.md`
- The added `r2` replicate ran in reversed mode order (`subagents -> single_xhigh`) on the stabilized `round4` seed.
- In that `r2`, `single_xhigh` again won on adjusted wall time and total tokens.
- The follow-on blind judged packet for that same `r2` pair now lives in `E:\agent_misc\benchmarks\results\20260323T133836Z_judge_packets`, and its deblinded judged analysis again preferred `subagents`.

## Notes

- This round reuses the second feature-round seed as its base so the benchmark agent inherits the already-stabilized runtime and SQLite test support.
- The harness now pins `gpt-5.4` plus explicit reasoning effort for every mode, so this batch should be directly comparable within itself.
- The harness now also supports a benchmark-scoped isolated `CODEX_HOME`; the validated path is to bootstrap only `auth.json`, `config.toml`, `cap_sid`, and `version.json` from the user's global `~/.codex` into the isolated home, rather than letting runs touch the broken global `state_5.sqlite`.
- Keep the current single-mode prompt wording intact for this round; do not soften the explicit "Do not spawn or use subagents." instruction.
- Do not mutate the active round-3 seed while this batch is still running. A stabilized follow-on seed for future runs now lives at `E:\agent_misc\.tmp_test\mail4agent_feature_round4_20260323`.
- Future reruns of these three task ids should now resolve to `E:\agent_misc\.tmp_test\mail4agent_feature_round4_20260323` in `E:\agent_misc\benchmarks\tasks.toml`, while still using the benchmark-scoped `E:\agent_misc\benchmarks\.codex_home` by default.

## Validation Entry Points

- `python -m unittest test.test_retry_queue_visibility -v`
- `python -m unittest test.test_thread_summary_and_unread_state -v`
- `python -m unittest test.test_webhook_or_stdio_bridge_delivery -v`
