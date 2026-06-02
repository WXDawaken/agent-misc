# Subagent Benchmark Report 2026-03-19

## Run Scope

- Results directory: `E:\agent_misc\benchmarks\results\20260319T114820Z`
- Tasks: `6`
- Modes: `single_xhigh`, `subagents`
- Replicates: `1` per task/mode pair
- Validation status: `12/12` passed

This report uses two quota proxies:

- Broad quota pressure: `total_tokens`
- Stricter new-context pressure: `fresh_input_tokens = input_tokens - cached_input_tokens`

## Headline

For this first full-suite pass, `single_xhigh` is the better default for `small` and `medium` work. It finished faster overall and also consumed fewer tokens overall.

`subagents` only started to show a credible efficiency advantage on part of the `large` bucket, where it was still slower but sometimes cheaper in token terms. The clearest example was `large_end_run_summary`, where `subagents` spent about `209k` fewer total tokens while finishing about `22s` slower.

## Overall Totals

| Mode | Runs | Success | Total Wall (s) | Median Wall (s) | Total Tokens | Total Fresh Input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_xhigh` | 6 | 100.0% | 1637.223 | 264.543 | 2,422,360 | 200,107 |
| `subagents` | 6 | 100.0% | 2077.883 | 329.889 | 2,900,078 | 233,294 |

Readout:

- `single_xhigh` was about `440.660s` faster in aggregate.
- `single_xhigh` used `477,718` fewer total tokens in aggregate.
- `single_xhigh` also used `33,187` fewer fresh input tokens in aggregate.

For a rough GPT subscription-pressure comparison, both token proxies still favor `single_xhigh` on this dataset.

## By Scale

### Small

| Mode | Total Wall (s) | Median Wall (s) | Total Tokens | Total Fresh Input |
| --- | ---: | ---: | ---: | ---: |
| `single_xhigh` | 467.422 | 233.711 | 571,904 | 71,465 |
| `subagents` | 542.727 | 271.363 | 794,681 | 75,247 |

Interpretation:

- `single_xhigh` is the clear default for `small`.
- One `small` task had faster wall-clock with `subagents`, but not lower total token use.

### Medium

| Mode | Total Wall (s) | Median Wall (s) | Total Tokens | Total Fresh Input |
| --- | ---: | ---: | ---: | ---: |
| `single_xhigh` | 496.098 | 248.049 | 731,884 | 40,211 |
| `subagents` | 800.457 | 400.228 | 1,174,661 | 83,561 |

Interpretation:

- `single_xhigh` clearly leads on both time and quota proxies.
- This bucket is the strongest evidence against using subagents by default for moderate-scoped work.

### Large

| Mode | Total Wall (s) | Median Wall (s) | Total Tokens | Total Fresh Input |
| --- | ---: | ---: | ---: | ---: |
| `single_xhigh` | 673.703 | 336.851 | 1,118,572 | 88,431 |
| `subagents` | 734.699 | 367.350 | 930,736 | 74,486 |

Interpretation:

- `single_xhigh` still wins on wall-clock time.
- `subagents` wins on both total tokens and fresh input tokens.
- This is the first bucket where the answer changes depending on whether you optimize for time or quota burn.

## Task-Level Notes

- `single_xhigh` was faster on `5/6` comparable task pairs.
- `single_xhigh` used fewer total tokens on `5/6` comparable task pairs.
- `subagents` only clearly won the token side on `large_end_run_summary`.
- `large_battery_pickups` did not repeat that win; it was slower and slightly more expensive in total tokens, though it did use fewer fresh input tokens.

## Recommendation

Use this as the current operating policy:

1. Default to `single_xhigh` for `small` and `medium` tasks.
2. Consider `subagents` for `large` tasks when token pressure matters more than absolute turnaround time.
3. Do not generalize the `large` result too broadly yet; the token benefit was not consistent across both `large` tasks.
4. Treat this as an objective-efficiency readout only. A blinded judged-quality pass is still needed before calling one mode strictly better.

## Next Steps

1. Add `2-3` more replicates for the `large` tasks only.
2. Run the planned judged-quality pass on saved artifacts without exposing mode labels.
3. Keep using `E:\agent_misc\benchmarks\analyze_benchmark_results.py` so future runs stay on the same reporting schema.
