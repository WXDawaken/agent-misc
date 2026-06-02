# Web Port Large Task Batch 2026-03-20

## Scope

This note records the first objective benchmark pass for the web-port large-task batch.

Update on `2026-03-21`:

- operator-polish rerun and recovery details now live in `E:\agent_misc\docs\subagent-web-port-operator-polish-recovery-20260321.md`
- use that follow-up note for the `r3` bug-exposure pair and the recovered `r4` comparison pair
- the first deblinded judged-quality follow-up now lives in `E:\agent_misc\docs\subagent-web-port-large-task-judged-quality-20260321.md`
- use that judged note plus `E:\agent_misc\benchmarks\results\20260321T051500Z_web_port_large_current_judge_packets\judged_analysis.md` for the current quality readout

Included result directories:

- `E:\agent_misc\benchmarks\results\20260320T132500Z`
- `E:\agent_misc\benchmarks\results\20260320T135049Z`

Combined analysis directory:

- `E:\agent_misc\benchmarks\results\20260320T155200Z_web_port_large_round1_combined`

Task set:

- `large_web_port_vertical_slice`
- `large_web_port_replay_parity_workbench`
- `large_web_port_operator_polish`

Modes:

- `single_xhigh`
- `subagents`

Replicates in this note:

- `1` per task/mode pair

All six runs exited cleanly and passed their task-specific validation commands.

## Headline

On this first web-port large-task pass, `subagents` is ahead overall on both raw median wall-clock time and conservative network-adjusted median wall-clock time, along with total tokens and fresh input tokens.

That is already a different shape from the earlier console-only `large` bucket, where `single_xhigh` remained the safer default.

Current first-pass totals:

| Mode | Runs | Success | Median Wall (s) | Median Wall Adj (s) | Total Tokens | Total Fresh Input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_xhigh` | `3` | `100%` | `1498.681` | `1498.487` | `9,856,326` | `665,712` |
| `subagents` | `3` | `100%` | `1414.040` | `1414.040` | `7,744,481` | `401,283` |

Logged network retry backoff totaled `1.397s` across `3` of the `6` runs, and subtracting that conservative jitter estimate did not change any task-level winner ordering in this batch.

## Task-Level Readout

### `large_web_port_vertical_slice`

- `single_xhigh` was faster by `119.392s`
- `single_xhigh` used `104,263` fewer total tokens
- `subagents` used `41,183` fewer fresh input tokens

Interpretation:

- the first browser-playable slice is still compressible enough that single-thread execution remains competitive
- subagents did not buy back their coordination overhead on total tokens here

### `large_web_port_replay_parity_workbench`

- `subagents` was faster by `84.641s`
- `single_xhigh` used `758,034` fewer total tokens
- `single_xhigh` used `63,887` fewer fresh input tokens

Interpretation:

- the replay/parity task shows a split decision
- delegation helped turnaround time, but not quota pressure

### `large_web_port_operator_polish`

- `subagents` was faster by `848.376s`
- `subagents` used `2,974,142` fewer total tokens
- `subagents` used `287,133` fewer fresh input tokens

Interpretation:

- this is the clearest early win for `subagents`
- once the round becomes UI-heavy, summary-heavy, and cross-surface enough, the coordination cost is repaid decisively on this sample

## First Conclusion

The new large-task batch is already doing what it was meant to do:

- it produces a materially different efficiency picture from the old console-only `large` bucket
- it creates task-level separation instead of one vague "large task" average
- it suggests that end-to-end web-port work may be the first workload family in this repo where `subagents` can be the better default on objective efficiency, not just on routing curiosity

Important limit:

- this is still only one replicate per task/mode pair
- there is still no blinded judged-quality pass

## Recommended Next Steps

1. Add at least `2` more replicates per task/mode pair for this same three-task batch.
2. Prioritize confirming whether the large `operator_polish` subagent advantage persists on rerun.
3. Run the planned judged-quality pass on the six saved artifact sets before calling `subagents` categorically better for web-port large work.
4. Keep recording subagent topology, but do not let topology replace outcome metrics as the headline.
