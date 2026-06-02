# Web Port Large Task Judged Quality 2026-03-21

## Scope

This note records the first deblinded judged-quality readout for the current successful large web-port comparison set.

Public judge bundle:

- `E:\agent_misc\benchmarks\results\20260321T051500Z_web_port_large_current_judge_packets`

Deblinded judged analysis:

- `E:\agent_misc\benchmarks\results\20260321T051500Z_web_port_large_current_judge_packets\judged_analysis.md`

Objective comparison baseline for the same successful run set:

- `E:\agent_misc\benchmarks\results\20260321T130000Z_web_port_large_current_combined\analysis.md`

## Headline

On this first blinded judged-quality pass, `subagents` is ahead overall.

Across the twelve judged candidates:

| Mode | Candidates | Preferred Pairs | Mean Score (5) | Median Score (5) | Mean Q/1k Tokens | Mean Q/Minute |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_xhigh` | `6` | `1` | `4.333` | `4.375` | `0.002313` | `0.208` |
| `subagents` | `6` | `5` | `4.792` | `4.875` | `0.002358` | `0.223` |

That means the judged pass aligns with the current objective readout rather than reversing it:

- `subagents` was preferred on `5` of `6` blinded pair comparisons
- `subagents` had the higher mean judged score and the higher median judged score
- `subagents` also came out ahead on judged quality per minute and judged quality per 1k tokens on this sample

## Task-Level Readout

### `large_web_port_operator_polish`

- `subagents` won both judged pairs
- score deltas were `+4` on `r1` and `+1` on the recovered `r4`
- mean judged score was `4.750` for `subagents` versus `4.125` for `single_xhigh`

Interpretation:

- the judged pass agrees with the objective rerun story that operator polish is currently the clearest `subagents` win in this workload family

### `large_web_port_replay_parity_workbench`

- `subagents` won both judged pairs
- score deltas were `+2` on `r1` and `+1` on `r2`
- mean judged score was `4.875` for `subagents` versus `4.500` for `single_xhigh`

Interpretation:

- this judged pass breaks the earlier objective split in favor of `subagents`
- the main judged advantage came from stronger parity evidence and more complete replay-facing delivery

### `large_web_port_vertical_slice`

- pair preference split `1 : 1`
- `subagents` won `r1` by `+4`
- `single_xhigh` won `r2` by `+1`
- mean judged score still favored `subagents`, `4.750` versus `4.375`

Interpretation:

- vertical slice remains the least settled task family
- `single_xhigh` still has a credible path here, especially when the slice stays compact and the browser behavior can be evidenced cleanly

## Current Conclusion

The judged pass strengthens the current case for `subagents` as the working default for large web-port delivery tasks in this repo.

Why:

- the earlier objective comparison already favored `subagents` overall on network-adjusted wall-clock time and total tokens
- the new judged pass also favors `subagents` on pairwise preference, mean judged score, median judged score, and judged quality per minute
- the two task families that most resemble richer cross-surface web-port work, `operator_polish` and `replay_parity_workbench`, both judged in favor of `subagents` on every saved pair

Important limits:

- this is still only one blinded Codex judge pass, not a human multi-rater review
- replicate count is still small
- some packets carried empty secondary validation logs, so evidence scores partly reflect artifact completeness
- `large_web_port_vertical_slice` is still mixed enough that a task-type split remains more defensible than a universal blanket rule

## Recommendation

Use the current evidence this way:

1. Treat `subagents` as the provisional default for large web-port tasks that are UI-heavy, parity-heavy, or cross-surface.
2. Keep `single_xhigh` as a live option for compact vertical-slice tasks where a tight single-thread implementation can still be cleaner.
3. Add at least one more replicate and, if possible, one independent human judged pass before calling the policy fully settled.
