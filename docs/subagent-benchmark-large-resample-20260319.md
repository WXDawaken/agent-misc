# Large Benchmark Resample 2026-03-19

## Scope

This addendum extends the original full-suite report in [subagent-benchmark-report-20260319.md](E:\agent_misc\docs\subagent-benchmark-report-20260319.md).

Included successful `large` result sets:

- `E:\agent_misc\benchmarks\results\20260319T114820Z`
- `E:\agent_misc\benchmarks\results\20260319T131457Z`
- `E:\agent_misc\benchmarks\results\20260319T132530Z`
- `E:\agent_misc\benchmarks\results\20260319T133956Z`

Attempted but excluded:

- `E:\agent_misc\benchmarks\results\20260319T135932Z`

The excluded set hit a Codex usage limit and both runs exited with `codex_return_code = 1`, `0` tokens, and no code changes. It should not be treated as a valid efficiency sample.

## Combined Large-Only Readout

Successful `large` runs counted:

- `single_xhigh`: `5`
- `subagents`: `5`

| Mode | Total Wall (s) | Median Wall (s) | Total Tokens | Median Tokens | Total Fresh Input | Median Fresh Input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_xhigh` | 1685.387 | 320.584 | 2,715,953 | 502,813 | 248,523 | 31,770 |
| `subagents` | 2266.349 | 391.762 | 2,915,643 | 524,331 | 298,785 | 50,335 |

Headline:

- After resampling, `single_xhigh` is ahead on both time and token use across the combined `large` pool.
- The earlier idea that `subagents` might broadly win the `large` bucket on quota burn no longer holds up on the current sample.

## Pairwise Readout

Valid comparable `large` pairs: `5`

### `large_end_run_summary`

Runs available per mode: `3`

| Mode | Median Wall (s) | Median Tokens | Median Fresh Input |
| --- | ---: | ---: | ---: |
| `single_xhigh` | 245.035 | 341,818 | 20,028 |
| `subagents` | 367.364 | 515,858 | 24,791 |

Interpretation:

- The original one-off token win for `subagents` did not replicate.
- On the current sample, `single_xhigh` is better on time, total tokens, and fresh input.

### `large_battery_pickups`

Runs available per mode: `2`

| Mode | Median Wall (s) | Median Tokens | Median Fresh Input |
| --- | ---: | ---: | ---: |
| `single_xhigh` | 453.064 | 756,018 | 88,712 |
| `subagents` | 488.423 | 579,303 | 72,586 |

Interpretation:

- This task still shows the clearest `subagents` quota advantage.
- The tradeoff is stable so far: `single_xhigh` is somewhat faster, while `subagents` uses fewer total and fresh-input tokens.

## Updated Recommendation

Use this instead of the earlier broad `large` bucket takeaway:

1. Keep `single_xhigh` as the default even for `large` tasks unless you already know the task has a coordination-heavy shape like `large_battery_pickups`.
2. Treat `subagents` as a task-specific quota optimization, not a general `large`-task default.
3. Resume the interrupted extra `large_battery_pickups` sample after the usage window reopens so that task reaches `3` successful replicates per mode.

## Notes

- During this resample, the benchmark harness was hardened in two ways:
  - `status.json` writes now retry briefly on Windows to avoid transient file-lock failures.
  - Success accounting now requires both a clean Codex exit and passing validation commands.
