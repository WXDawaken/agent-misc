# Web Port Operator Polish Recovery 2026-03-21

## Scope

This note records the matched failure and recovery follow-up for `large_web_port_operator_polish`.

Relevant result directories:

- `E:\agent_misc\benchmarks\results\20260321T024022Z`
- `E:\agent_misc\benchmarks\results\20260321T034147Z`

Combined analysis directory:

- `E:\agent_misc\benchmarks\results\20260321T124500Z_operator_polish_recovery_combined`

## Failure Pair

The first targeted rerun in `20260321T024022Z` failed validation in both modes even though both top-level Codex runs exited with `0`.

Shared failure mode:

- `test_http_server_serves_state_and_processes_commands`
- `ConnectionResetError 10054` while requesting the `/api/reset` response

Root cause:

- both generated workspaces left the `/api/reset` POST body unread before writing the response
- on Windows, the keep-alive validation flow could then reset the connection when the client tried to read the response

Important interpretation:

- treat `20260321T024022Z` as bug-exposure evidence, not as a clean efficiency comparison
- the old harness-side decode bug was fixed separately, but that only revealed the real validation failure more clearly

## Fix

The round-6 operator-polish template at `E:\agent_misc\.tmp_test\web_port_round6_20260320` now discards unread `/api/reset` POST bodies before returning the reset payload.

Targeted verification on the fixed template:

- `python -m unittest test.test_salvage_run_web.SalvageRunWebTests.test_http_server_serves_state_and_processes_commands -v` passed
- a 30-iteration local keep-alive repro loop with `POST /api/reset` carrying `b"{}"` completed with `0` failures

## Recovery Pair

The recovery rerun in `20260321T034147Z` passed validation in both modes.

Current objective readout:

| Mode | Success | Wall (s) | Total Tokens | Fresh Input |
| --- | ---: | ---: | ---: | ---: |
| `single_xhigh` | `100%` | `1787.281` | `7,356,693` | `214,163` |
| `subagents` | `100%` | `1250.805` | `4,016,548` | `303,896` |

Recovery-pair interpretation:

- `subagents` was faster by `536.476s`
- `subagents` used `3,340,145` fewer total tokens
- `single_xhigh` still used fewer fresh input tokens
- neither recovered run showed logged network retry backoff

## Combined Readout

The combined operator-polish analysis in `20260321T124500Z_operator_polish_recovery_combined` keeps both the matched failure pair and the recovered pair in one place.

Use it for:

- documenting why `r3` should not be treated as a fair mode comparison
- preserving the exact failure evidence that motivated the template fix
- keeping the recovered `r4` pair attached to the same incident trail

Do not use the aggregate success rate in that combined file as a product-performance headline by itself, because it intentionally mixes one bug-exposure pair with one recovered pair.

## Current Conclusion

For operator polish specifically:

- `r3` is a matched repeated-failure pair caused by a workload bug
- `r4` is the current objective comparison pair after the fix
- under that recovered comparison, `subagents` remains ahead on solve time and total tokens

## Next

1. Keep `20260321T024022Z` as the bug-exposure record.
2. Use `20260321T034147Z` as the current operator-polish performance readout.
3. Fold `20260321T034147Z` into the next broader large-task combined analysis.
4. Add more replicates and a judged-quality pass before changing any default policy.
