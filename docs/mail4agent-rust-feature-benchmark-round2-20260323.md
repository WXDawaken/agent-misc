# Mail4Agent Rust Feature-Port Round 2

## Goal

Test whether the current `mail4agent` feature extensions can be ported onto the native Rust mailbox-server slice instead of only existing in the Python server.

This round is intentionally different from the first Rust line:

- round 1 asked whether agents could build Rust client, worker, and server vertical slices
- this round asks whether agents can carry already-defined Python product features across that Rust server boundary

## Current Batch Shape

This first Rust feature-port batch maps the current round-3 Python feature line into three Rust-port tasks:

- `small_mail4agent_rust_retry_queue_visibility`
- `medium_mail4agent_rust_thread_summary_and_unread_state`
- `large_mail4agent_rust_webhook_or_stdio_bridge_delivery`

## Seed Strategy

These tasks do not start from the old pre-feature Python seeds.

Instead, each task uses its own feature-specific template workspace:

- the corresponding completed Python feature workspace provides the current behavior contract, client commands, docs, and tests
- the validated native Rust mailbox-server workspace from `large_mail4agent_rust_server_vertical_slice__single_xhigh__r2__workspace` is overlaid on top as the Rust baseline

This avoids mixing two problems:

- rebuilding the Python feature surface from scratch
- porting that already-known feature behavior onto the Rust server

## Current Templates

- small retry queue:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_retry_queue_round1_20260323`
- medium thread summary:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_thread_summary_round1_20260323`
- large bridge delivery:
  - `E:\agent_misc\.tmp_test\mail4agent_rust_bridge_round1_20260323`

All three tasks share:

- manifest: `E:\agent_misc\benchmarks\mail4agent_rust_feature_workspace_manifest.toml`
- isolated benchmark `CODEX_HOME`
- explicit parent-agent model pinning from the current harness

## Validation Model

Each validation path seeds the SQLite database with the Python `SQLiteMailbox` helper, launches the Rust server binary, and then drives the current Python feature client/tests against that Rust server.

That means the benchmark measures feature-port fidelity against the current Python contract, not whether the agent can invent a new Rust-only surface.

## First Planned Launch Policy

Start with a small `single_xhigh` probe first.

The goal of that first run is to answer one narrow question:

- can the current Rust vertical-slice baseline absorb one of the mailbox feature extensions cleanly?

If the small probe passes, medium and large can follow under the same explicit-config harness.

## Current Launch Status

- The first launch attempt exposed a template-manifest mismatch:
  - the shared Rust feature manifest required `codex_mailbox_demo_agent.py` and `codex_mailbox_demo_send.py`
  - the feature-specific seeds did not yet include those two reference files
  - the benchmark process exited during workspace materialization, leaving a stale `preparing` status in `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small\20260323T142601Z`
- That mismatch is now fixed by restoring those two reference files into all three Rust feature seeds.
- The corrected small probe is now in flight:
  - task: `small_mail4agent_rust_retry_queue_visibility`
  - results roots:
    - `single_xhigh`: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small_rerun\20260323T145158Z`
    - `subagents`: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small_subagents\20260323T150441Z`

## First Paired Readout

The first paired Rust feature-port readout is now complete for `small_mail4agent_rust_retry_queue_visibility`.

Objective comparison:

- Combined analysis: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small_combined\analysis.md`
- `single_xhigh`: `381.739s`, `1,150,071` total tokens, `54,438` fresh input tokens
- `subagents`: `500.467s`, `1,945,255` total tokens, `283,226` fresh input tokens
- Both passed objective validation.

Solve-path note:

- `single_xhigh` stayed on a direct local loop after first reproducing the missing `POST /nack` route; it then added `POST /nack`, `GET /retry-queue`, query percent-decoding, and the bridge ops, followed by a single benchmark validation run.
- `subagents` did launch helper readers successfully after two initial spawn failures, but the parent still performed the implementation locally; that advisory coordination overhead did not pay off on this small Rust task.

Blinded judged-quality comparison:

- Judge packet bundle: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small_judge_packets`
- Deblinded readout: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_small_judge_packets\judged_analysis.md`
- Pair preference favored `single_xhigh` on `1/1` judged pairs.
- Judge rationale favored the candidate whose packet had tighter evidence alignment and concrete public validation support.

Current takeaway:

- On this first Rust feature-port small task, `single_xhigh` beat `subagents` on both objective metrics and the first blinded judged pass.
- So this task does not support the idea that `subagents` are already stably preferred on Rust feature-port work.

## Second Paired Readout

The second paired Rust feature-port readout is now complete for `medium_mail4agent_rust_thread_summary_and_unread_state`.

Objective comparison:

- Results root: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_medium\20260323T152556Z`
- Objective analysis: `E:\agent_misc\benchmarks\results\20260323T_mail4agent_rust_feature_round2_medium\20260323T152556Z\analysis.md`
- `single_xhigh`: `865.509s`, `2,250,734` total tokens, `326,224` fresh input tokens
- `subagents`: `1058.847s`, `4,288,433` total tokens, `391,921` fresh input tokens
- Both passed objective validation.

Solve-path note:

- `single_xhigh` stayed local, ported `GET /thread-summaries` plus `POST /mark-thread-read` directly into the Rust app and bridge, and then closed the loop with `cargo fmt`, `cargo build`, and the benchmark unittest.
- `subagents` did eventually launch explicit-context helper readers, but only after two initial spawn failures; the parent still owned the implementation and also had to absorb a Cargo dependency/network detour before the build stabilized.

Blinded judged-quality comparison:

- Judge packet bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_medium_judge_packets`
- Deblinded readout: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_medium_judge_packets\judged_analysis.md`
- Pair preference favored `single_xhigh` on `1/1` judged pairs.
- Judge rationale favored the candidate that reused shared address and auth helpers more tightly while delivering the same validated feature surface.

Current takeaway:

- On this second Rust feature-port task, `single_xhigh` again beat `subagents` on objective wall-clock, total tokens, fresh input tokens, and the blinded judged pass.
- Across the completed small plus medium Rust feature-port tasks, there is still no evidence that `subagents` are already stably preferred on this line.

## Third Paired Readout

The third paired Rust feature-port readout is now complete for `large_mail4agent_rust_webhook_or_stdio_bridge_delivery`.

Objective comparison:

- Results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large\20260323T161019Z`
- Objective analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large\20260323T161019Z\analysis.md`
- `single_xhigh`: `876.290s`, `3,403,090` total tokens, `255,478` fresh input tokens
- `subagents`: `385.923s`, `973,554` total tokens, `104,221` fresh input tokens
- Both passed objective validation.

Solve-path note:

- `single_xhigh` implemented the bridge retry and lease-extension path on the compiled Rust server directly, but it carried a larger serial path: more changed files, more events, and a broader delivery summary that included extra README guidance plus a follow-on vertical-slice regression run.
- `subagents` still delegated only bounded helper reading, but the parent converged much faster on the narrow missing surface: `nack`, `heartbeat`, the required bridge test tightening, and a small test-harness cleanup to remove lingering pipe-handle warnings from the public validation evidence.

Blinded judged-quality comparison:

- Judge packet bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_judge_packets`
- Deblinded readout: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_judge_packets\judged_analysis.md`
- Pair preference favored `subagents` on `1/1` judged pairs.
- Judge rationale favored the narrower candidate that still passed the same bridge suite while also cleaning the pipe-handle warning noise in the bundled evidence.

Current takeaway:

- On this third Rust feature-port task, `subagents` beat `single_xhigh` on objective wall-clock, total tokens, fresh input tokens, and the blinded judged pass.
- The Rust feature-port line now shows a clear shape split: `single_xhigh` won the completed small plus medium tasks, while `subagents` won this first large bridge-delivery task on both objective and judged readouts.

## Large Replicate `r2`

The follow-on `r2` replicate is now complete for `large_mail4agent_rust_webhook_or_stdio_bridge_delivery`.

Objective comparison:

- Results root: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_r2\20260323T184223Z`
- This pair ran in reversed mode order via `--replicate-start 2 --alternate-mode-order`, so the sequence was `subagents -> single_xhigh`.
- `subagents`: `377.403s`, `1,552,872` total tokens, `63,811` fresh input tokens
- `single_xhigh`: `346.175s`, `971,439` total tokens, `54,621` fresh input tokens
- Both passed objective validation.

Blinded judged-quality comparison:

- Judge packet bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_r2_judge_packets`
- Deblinded readout: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_r2_judge_packets\judged_analysis.md`
- Pair preference again favored `subagents` on `1/1` judged pairs.
- Judge rationale favored the candidate whose extra test change directly exercised heartbeat during `bridge-once`, rather than spending the extra surface area on harness cleanup.

## Current Combined Large-Bridge Readout

Across `r1 + r2`, the objective and judged story now separates cleanly.

Objective comparison:

- Combined analysis: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_combined\analysis.md`
- Pairwise objective winners are split `1 : 1`.
- Even with that split, the aggregate objective medians and total/fresh token counts still favor `subagents`, because the `r1` gap was materially larger than the `r2` reversal.

Judged-quality comparison:

- `r1` judged bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_judge_packets\judged_analysis.md`
- `r2` judged bundle: `E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_feature_round2_large_r2_judge_packets\judged_analysis.md`
- Judged pair preference is now `2 : 0` for `subagents`.

Current takeaway:

- The large Rust bridge task no longer supports a stable objective winner; `r1` favored `subagents`, while the reversed-order `r2` favored `single_xhigh`.
- But the judged signal is more consistent: both blinded judged passes preferred `subagents`.
- So the current best framing for this task is not "single wins" or "subagents win" globally, but "objective is replicate-sensitive while judged quality still leans `subagents`."

## Recommended Next Batch

The current bridge result is now strong enough to stop adding bridge-only replicates for the moment.

The next useful batch should test task shape instead:

- `large_mail4agent_rust_export_import_environment_bundle`
- `large_mail4agent_rust_delivery_audit_timeline`
- `medium_mail4agent_rust_routing_explain_surface`

That slate is tracked in:

- `E:\agent_misc\docs\mail4agent-rust-feature-followup-tests-20260324.md`
