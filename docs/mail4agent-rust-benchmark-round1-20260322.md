# Mail4Agent Rust Benchmark Round 1

## Goal

Start the mailbox Rust benchmark line with a sender-first task that tests Rust fluency without immediately mixing in server migration complexity.

## Current Batch Shape

- Materialized now:
  - `small_mail4agent_rust_demo_sender_roundtrip`
  - `medium_mail4agent_rust_worker_heartbeat`
- Materialized next:
  - `large_mail4agent_rust_server_vertical_slice`

## Large-Run Policy

When the first large `mail4agent` Rust server slice runs, it should launch as a matched dual-mode batch:

- `single_xhigh`
- `subagents`

The goal of that large round is no longer Rust-only fluency in isolation. It is the first direct comparison point for how the two orchestration modes handle a larger Rust server migration task in the same seeded workspace.

## Materialized Small Task

- Task id: `small_mail4agent_rust_demo_sender_roundtrip`
- Template workspace: `E:\agent_misc\.tmp_test\mail4agent_rust_small_round1_20260322`
- Validation: `python -m unittest test.test_rust_demo_sender_roundtrip -v`
- Intent:
  - measure whether the agent can implement a small Rust CLI that talks to the existing Python mailbox oracle
  - focus on CLI parsing, HTTP JSON calls, reply matching, and machine-readable output

## Why This First

- It isolates Rust implementation quality better than a full server port.
- It reuses the existing Python server and demo agent as a protocol oracle.
- It gives a compact first read on whether `single_xhigh` can operate comfortably in Rust.

## Validation Model

The validation script seeds a temporary SQLite mailbox fixture, runs the Python mailbox server in-process, drives the Python demo agent as the reply oracle, and then builds plus runs the Rust sender binary.

The first objective checks are:

- `upper_text` roundtrip
- `sum_numbers` roundtrip with payload merge

## First Run Result

- Run id: `small_mail4agent_rust_demo_sender_roundtrip__single_xhigh__r1`
- Results dir: `E:\agent_misc\benchmarks\results\20260321T181001Z`
- Outcome: objective validation pass
- Wall time: `888.058s`
- Total tokens: `4,751,375`
- Fresh input tokens: `81,875`

The first `single_xhigh` run succeeded and passed `python -m unittest test.test_rust_demo_sender_roundtrip -v`.

One caveat: the agent spent part of the run adapting benchmark-environment details such as Cargo target output location and unittest temp/runtime paths. That still counts as useful Rust-and-tooling competence, but it means this first pass is not a perfectly pure read on application logic alone.

## Next If This Passes

- Run the first medium Rust worker benchmark on top of the successful sender baseline.
- Add one larger server-slice task so Rust-client and Rust-server skill can be compared separately.

## First Medium Run Result

- Run id: `medium_mail4agent_rust_worker_heartbeat__single_xhigh__r1`
- Results dir: `E:\agent_misc\benchmarks\results\20260322T035652Z`
- Outcome: objective validation pass
- Wall time: `778.846s`
- Total tokens: `1,766,440`
- Fresh input tokens: `53,428`

The first medium `single_xhigh` run also succeeded and passed `python -m unittest test.test_rust_demo_worker -v`.

This medium readout is cleaner than the first small run in one useful way: the agent spent less of the budget on environment scaffolding and more on the Rust worker itself. It still touched the Python validation file for the runtime root, but the bulk of the implementation landed in the new Rust modules under `rust_demo_worker/src/`.

## Large Task Status

- Task id: `large_mail4agent_rust_server_vertical_slice`
- Template workspace: `E:\agent_misc\.tmp_test\mail4agent_rust_large_round1_20260322`
- Validation: `python -m unittest test.test_rust_mailbox_server_vertical_slice -v`
- Planned modes: `single_xhigh` and `subagents`
- Launch status: completed
- Batch: `E:\agent_misc\benchmarks\results\20260322T042533Z`
- Analysis: `E:\agent_misc\benchmarks\results\20260322T042533Z\analysis.md`

This large seed already carries forward the successful Rust sender and worker baselines, so the next agent starts from a mailbox repo that already has working Rust client-side slices and can focus on the server vertical slice.

## First Large Run Result

- `single_xhigh`: validation pass, `2078.248s`, `7,523,753` total tokens
- `subagents`: validation pass, `2512.643s` network-adjusted wall, `6,754,397` total tokens

The first large paired run produced a mixed tradeoff instead of a clean winner. `single_xhigh` was faster by about `434s`, while `subagents` used about `769k` fewer total tokens and fewer fresh input tokens.

That makes this first large Rust readout directionally different from the earlier judged large web-port batch: here, the current evidence says `single_xhigh` may still be the better default if elapsed time matters more, while `subagents` remains attractive if token pressure matters more.

This is still only one comparable pair, and there is no judged-quality pass yet for the large Rust slice.

## Second Large Run Result

- Batch: `E:\agent_misc\benchmarks\results\20260322T060155Z_mail4agent_large_r2\20260322T060156Z`
- `single_xhigh`: validation pass, `2246.514s`, `7,819,229` total tokens
- `subagents`: validation pass, `2082.564s` network-adjusted wall, `6,249,830` total tokens

The second large paired run flipped the speed result from `r1`: this time `subagents` was faster and still used fewer total tokens.

## Current Combined Large Readout

- Combined objective analysis: `E:\agent_misc\benchmarks\results\20260322T071600Z_mail4agent_large_r1_r2_combined\analysis.md`
- Blind judged bundle: `E:\agent_misc\benchmarks\results\20260322T071700Z_mail4agent_large_judge_packets`
- Deblinded judged analysis: `E:\agent_misc\benchmarks\results\20260322T071700Z_mail4agent_large_judge_packets\judged_analysis.md`

Across `r1 + r2`, the objective picture is still split:

- `single_xhigh` keeps the lower adjusted median wall time
- `subagents` uses fewer total tokens in both comparable pairs
- the first blinded judged pass gives one pair preference to each mode, but the average judged score still favors `subagents`

For now, the safest interpretation is that this large Rust slice is still mode-sensitive rather than settled.
