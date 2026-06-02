# Mail4Agent Large Rust Eval

## Scope

This note captures the first two objective paired runs plus the first blinded judged-quality pass for `large_mail4agent_rust_server_vertical_slice`.

## Objective Inputs

- `r1`: `E:\agent_misc\benchmarks\results\20260322T042533Z`
- `r2`: `E:\agent_misc\benchmarks\results\20260322T060155Z_mail4agent_large_r2\20260322T060156Z`
- Combined objective analysis: `E:\agent_misc\benchmarks\results\20260322T071600Z_mail4agent_large_r1_r2_combined\analysis.md`

## Objective Readout

- Both modes passed objective validation in both replicates.
- `single_xhigh` won elapsed time in `r1`.
- `subagents` won elapsed time in `r2`.
- Across the two-pair combined readout, `single_xhigh` still had the lower adjusted median wall time: `2162.381s` versus `2297.604s`.
- Across the same combined readout, `subagents` used fewer total tokens in both pairs and fewer total tokens overall: `13,004,227` versus `15,342,982`.

This leaves the objective picture as a split tradeoff rather than a clean mode winner.

## Blind Judged Bundle

- Bundle: `E:\agent_misc\benchmarks\results\20260322T071700Z_mail4agent_large_judge_packets`
- Deblinded judged analysis: `E:\agent_misc\benchmarks\results\20260322T071700Z_mail4agent_large_judge_packets\judged_analysis.md`

## Judged Readout

- The blinded judge preferred `single_xhigh` on one pair and `subagents` on one pair.
- Average judged score still favored `subagents`: `4.125` versus `3.750`.
- Judged quality per minute and per 1k tokens also favored `subagents`.
- The strongest recurring criticism on the weaker candidates was unnecessary inactive surface area around alternate mains, per-request Python bridge spawning, or extra unused helper modules.

## Current Working Conclusion

For this large Rust mailbox-server slice, the current evidence does not support a one-line global winner yet.

- If elapsed time matters more, `single_xhigh` still looks slightly stronger on the two-pair objective readout.
- If implementation compactness and judged quality matter more, the first blinded pass leans toward `subagents`.

The next useful step would be either:

- add one more replicate, or
- run a second independent judged pass before setting any default policy for large Rust migration work.
