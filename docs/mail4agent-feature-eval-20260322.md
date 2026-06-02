# Mail4Agent Feature Extension Eval

## Batch

- Results dir: `E:\agent_misc\benchmarks\results\20260322T082714Z`
- Analysis: `E:\agent_misc\benchmarks\results\20260322T082714Z\analysis.md`
- Judge bundle: `E:\agent_misc\benchmarks\results\20260322T100300Z_judge_packets`
- Judged analysis: `E:\agent_misc\benchmarks\results\20260322T100300Z_judge_packets\judged_analysis.md`
- Tasks:
  - `small_mail4agent_inbox_list_and_filters`
  - `medium_mail4agent_routing_explain_surface`
  - `large_mail4agent_delivery_audit_timeline`

## Config Caveat

This memo predates the harness change that now records `resolved_model` / `resolved_reasoning_effort` and explicitly passes reasoning effort into Codex CLI for every run.

That means this earlier feature-extension batch should be treated as a useful but provisional read: it may reflect the then-current inherited global reasoning setting rather than a fully pinned benchmark configuration.

Newer sanity reruns under the explicit-config harness now live in:

- `E:\agent_misc\benchmarks\results\20260323T_simple_config_sanity\20260322T174804Z`
- `E:\agent_misc\benchmarks\results\20260323T_large_config_sanity\20260322T182520Z`

Those reruns do not directly replace this batch because they cover different tasks, but they do show that some earlier cross-mode comparisons may contain configuration-driven regression or comparability noise.

## Objective Readout

- All `6/6` runs completed successfully and passed objective validation.
- In this first matched batch, `single_xhigh` beat `subagents` on adjusted wall time for all three comparable pairs.
- In this first matched batch, `single_xhigh` also used fewer total tokens for all three comparable pairs.
- `subagents` only led on fresh input tokens in the small inbox-filter task; medium and large still favored `single_xhigh`.

## Pair Highlights

- `small_mail4agent_inbox_list_and_filters`
  - `single_xhigh`: `713.012s`, `3,041,198` total tokens
  - `subagents`: `995.178s` adjusted, `5,261,261` total tokens
- `medium_mail4agent_routing_explain_surface`
  - `single_xhigh`: `559.141s`, `2,456,125` total tokens
  - `subagents`: `642.031s`, `2,868,520` total tokens
- `large_mail4agent_delivery_audit_timeline`
  - `single_xhigh`: `869.921s`, `2,818,947` total tokens
  - `subagents`: `990.798s`, `3,434,072` total tokens

## Judged Readout

- The first blinded judged-quality pass also favored `single_xhigh` overall.
- Pair preference went `2 : 1` for `single_xhigh`.
- Mean judged score favored `single_xhigh`, `4.417` vs `3.833`.
- Median judged score also favored `single_xhigh`, `4.250` vs `3.500`.
- Quality per minute and quality per 1k tokens both favored `single_xhigh`.

## Judged Task Split

- `large_mail4agent_delivery_audit_timeline`
  - judged winner: `single_xhigh`
  - score delta: `19` vs `13`
- `medium_mail4agent_routing_explain_surface`
  - judged winner: `subagents`
  - score delta: `19` vs `17`
- `small_mail4agent_inbox_list_and_filters`
  - judged winner: `single_xhigh`
  - score delta: `17` vs `14`

## Current Read

- This first feature-extension batch points in the opposite direction from the earlier web-port judged readouts: for these Python mailbox product-surface tasks, `single_xhigh` is currently the stronger default candidate on both objective and blinded judged evidence.
- The main caveat is task shape, not batch-level direction: `medium_mail4agent_routing_explain_surface` was the one judged pair that preferred `subagents`, even though `single_xhigh` still won that pair on time and total tokens.
- This is still an early read: one objective batch and one blinded Codex judge pass, not a larger replicate set or human multi-rater study.
- It should also be read with the explicit-config caveat above: pre-pin runs may not be fully comparable to newer runs that now lock both model and reasoning effort.
