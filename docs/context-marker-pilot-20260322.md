# Context Marker Pilot

## Run 1

- Results dir: `E:\agent_misc\benchmarks\results\20260322T105230Z`
- Task: `large_mail4agent_delivery_audit_timeline`
- Mode: `single_xhigh`
- Context marker tag: `ctx-probe-20260322`

## Run 1 Outcome

- The pilot completed successfully and passed objective validation.
- The structured marker prompt and harness parsing both worked.
- The run emitted exactly one startup marker.
- The run emitted zero explicit compaction markers.

## Run 1 Metrics

- `context_marker_count = 1`
- `context_compaction_marker_count = 0`
- `wall_clock_sec = 1175.584`
- `total_tokens = 5,917,053`
- `input_tokens = 5,869,703`
- `event_count = 209`

## Run 2

- Results dir: `E:\agent_misc\benchmarks\results\20260322T120343Z`
- Task: `large_mail4agent_rust_server_vertical_slice`
- Mode: `single_xhigh`
- Context marker tag: `ctx-probe-20260322-rust`

## Run 2 Outcome

- The second pilot also completed successfully and passed objective validation.
- The marker prompt and parsing path worked again on a longer Rust server task.
- The run emitted exactly one startup marker.
- The run emitted zero explicit compaction markers.

## Run 2 Metrics

- `context_marker_count = 1`
- `context_compaction_marker_count = 0`
- `wall_clock_sec = 2518.003`
- `wall_clock_sec_adjusted = 2517.798`
- `total_tokens = 7,214,185`
- `input_tokens = 7,126,185`
- `event_count = 154`
- `network_retry_backoff_sec = 0.205`

## Run 3

- Results dir: `E:\agent_misc\benchmarks\results\20260322T125900Z_web_port_ctx_probe\20260322T125623Z`
- Task: `large_web_port_operator_polish`
- Mode: `single_xhigh`
- Context marker tag: `ctx-probe-20260322-web-op`

## Run 3 Outcome

- The third pilot also completed successfully and passed objective validation.
- The marker prompt and parsing path worked again on a noisier web-port workload.
- The run emitted exactly one startup marker.
- The run emitted zero explicit compaction markers.

## Run 3 Metrics

- `context_marker_count = 1`
- `context_compaction_marker_count = 0`
- `wall_clock_sec = 1725.926`
- `wall_clock_sec_adjusted = 1725.926`
- `total_tokens = 7,684,873`
- `input_tokens = 7,605,555`
- `event_count = 176`
- `network_retry_backoff_sec = 0.000`

## Interpretation

- This experiment family is now a repeated plumbing success across three different long-task workloads but still not a positive compaction detection.
- The startup marker proves the prompt injection and event parsing path are live across mailbox and web-port task families.
- Zero compaction markers does **not** prove that no context compression happened; it only means these runs did not leave explicit marker-based evidence of summary-driven reconstruction.

## Current Read

- The marker experiment is now safe to reuse in future benchmark runs.
- After three startup-only runs, the evidence is still a lower bound: explicit marker hits are meaningful, but repeated zeros remain inconclusive.
- The noisier web-port workload did not produce the first positive hit, so the next probe should only happen if we have a materially longer or more interruption-prone task family to test.
