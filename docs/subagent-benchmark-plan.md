---
id: subagent-benchmark-plan
title: Subagent Benchmark Plan
type: plan
workspace: root
domains:
  - benchmark
  - subagents
series:
  - subagent-benchmark
status: active
created: 2026-03-19
updated: 2026-03-24
summary: Define how to compare native subagent runs against a single high-effort agent on the same isolated tasks.
related:
  - benchmark-judge-rubric
  - root-mainline-plan
supersedes: []
artifact_paths: []
---

# Subagent Benchmark Plan

Define the benchmark design, metrics, controls, judging flow, and operational guidance for comparing `subagents` against `single_xhigh`.

## Index

- [Goal](#goal)
- [What To Measure](#what-to-measure)
- [Experimental Design](#experimental-design)
- [Scale Definition](#scale-definition)
- [Quality Review Protocol](#quality-review-protocol)
- [Recommended Reporting](#recommended-reporting)
- [Practical Notes](#practical-notes)
- [Starting Point](#starting-point)

## Goal

Compare two execution modes on the same isolated workspace and task suite:

- `subagents`: use the repo's native monitor-entry workflow and project-scoped agents
- `single_xhigh`: force a single agent to solve directly with very high reasoning effort and no subagents

The benchmark is meant to answer:

- At what task scale do subagents improve completion quality enough to justify extra coordination cost?
- At what task scale does a single high-effort agent stay faster or cheaper?

## What To Measure

Record the following per run:

- `setup_sec`: workspace provisioning time, recorded separately from solve time
- `wall_clock_sec`: total elapsed solve time
- `network_retry_backoff_sec`: explicit retry backoff logged by Codex when websocket sampling retries after a disconnect
- `wall_clock_sec_adjusted = max(0, wall_clock_sec - network_retry_backoff_sec)`: conservative solve time after subtracting only logged network retry backoff
- `input_tokens`
- `cached_input_tokens`
- `output_tokens`
- `total_tokens = input_tokens + output_tokens`
- `validation_pass`: whether the fixed validation command(s) succeeded
- `changed_files_count`
- `changed_lines_added`
- `changed_lines_removed`
- `final_message`: keep the raw last message for later review

For quality, use two layers:

1. Objective quality
- Did Codex finish with a clean process exit?
- Did the fixed validation command(s) pass?
- Did the run stay inside the requested scope?

2. Judged quality
- Use a separate blinded review pass on saved artifacts
- Score correctness, scope control, code quality, and evidence quality on a 1-5 scale
- Keep judge cost separate from solve cost

Do not collapse everything into one scalar first. Start with:

- success rate
- median wall-clock time on successful runs
- median network-adjusted wall-clock time on successful runs
- median total tokens on successful runs
- median judged quality on successful runs

Then add normalized views:

- `quality_per_1k_tokens = judged_quality / (total_tokens / 1000)`
- `quality_per_minute = judged_quality / (wall_clock_sec / 60)`

## Experimental Design

### Independent Variables

- `mode`: `subagents`, `single_xhigh`
- `scale`: `small`, `medium`, `large`
- `task_id`
- `replicate`

### Controls

- Same workspace snapshot at run start
- Fresh isolated workspace per run
- Same model family unless you are intentionally benchmarking model choice
- Same validation command(s)
- Same timeout budget
- Randomized run order across modes

### Workspace Isolation Backend

Support two backends in the harness:

- `copy`: copy the template workspace into a disposable run directory
- `git_worktree`: materialize a disposable worktree from a git-tracked baseline

Recommendation:

- Use `copy` when you want to benchmark against the current working tree, including local uncommitted edits.
- Use `git_worktree` when you want lower setup cost plus commit-pinned baselines with cleaner diff semantics.

### Recommended Sample Size

Minimum useful run set:

- 3 tasks per scale
- 3 replicates per task per mode

That gives:

- `3 scales * 3 tasks * 2 modes * 3 replicates = 54 runs`

If budget is tight, start with:

- 2 tasks per scale
- 2 replicates per task per mode

## Scale Definition

Use scale based on implementation breadth, not prompt length.

### Small

Expected shape:

- 1-2 code files
- 1-2 test updates
- no new subsystem

Typical examples:

- telemetry change
- message/help refinement
- scan/status output tweak

### Medium

Expected shape:

- 2-4 code files
- tests plus docs
- one gameplay rule or UI behavior extension

Typical examples:

- moderate AI tweak
- new read-only command behavior
- cross-file balancing change

### Large

Expected shape:

- 4+ touched files
- state, UI, tests, docs all involved
- new mechanic or end-to-end behavior

Typical examples:

- new pickup type
- end-of-run summary system
- inventory or resource mechanic

## Quality Review Protocol

Use the benchmark harness to save:

- the task spec
- raw JSONL event log
- final message
- validation output
- changed-file summary

Then run a separate blinded judge on those artifacts.

The current helper for this step is `E:\agent_misc\benchmarks\build_judge_packets.py`.
It builds:

- a public `packets/` directory with neutral task specs, sanitized final messages, sanitized validation logs, and copied changed files
- `score_sheet.csv` plus `pair_preferences.csv` for the judge
- a private `_admin/manifest.json` that keeps the mode mapping and raw artifact paths out of the public review bundle

For the current large web-port sample, the first packet bundle lives at `E:\agent_misc\benchmarks\results\20260321T051500Z_web_port_large_current_judge_packets`.

After the blind scoring pass is complete, deblind it with `E:\agent_misc\benchmarks\analyze_judged_quality.py`.
That helper reads the completed score sheet, pair preferences, private admin manifest, and source `summary.json` files to produce a judged-quality analysis JSON and markdown report.

Judge rubric:

- `correctness_1_to_5`
- `scope_control_1_to_5`
- `code_quality_1_to_5`
- `evidence_quality_1_to_5`
- `notes`

Important:

- Hide the execution mode from the judge if possible
- Do not include solve tokens/time in the judge packet
- Keep judge runs out of the main efficiency table

## Recommended Reporting

Report results by scale first, then by task.

Primary tables:

- success rate by mode and scale
- median wall-clock by mode and scale
- median network-adjusted wall-clock by mode and scale
- median total tokens by mode and scale
- median judged quality by mode and scale

Primary plots:

- wall-clock vs total tokens
- judged quality vs total tokens
- judged quality vs wall-clock

Best decision view:

- draw a Pareto frontier for each scale
- do not force a single winner if one mode is cheaper and the other is higher quality

## Practical Notes

- Use `--json` from `codex exec` so token usage can be parsed automatically.
- The current CLI emits `turn.completed.usage`, which is enough for solve-cost accounting.
- In this workspace, subagent runs can be measured from the top-level JSONL stream; keep the parsing logic at the turn level and sum usage events.
- Treat a run as successful only if `codex_return_code == 0` and the validation commands pass. A fast early failure with unchanged files must not count as success just because the baseline test suite is already green.
- Use `--ephemeral` so benchmark runs do not leave session state behind.
- Keep benchmark workspaces disposable and outside the template root.
- Keep `setup_sec` separate from `wall_clock_sec` so copying or worktree creation does not distort solve-time comparisons.
- Use `E:\agent_misc\benchmarks\workspace_manifest.toml` to keep the benchmark workspace lean and focused on the gameplay files under test.
- Keep task-specific `focus_paths` and `avoid_paths` in `E:\agent_misc\benchmarks\tasks.toml` so each run starts with a bounded edit surface.
- Use task-level `template_workspace` and `workspace_manifest` overrides in `E:\agent_misc\benchmarks\tasks.toml` when one benchmark batch needs seeded baselines from different workload milestones.
- The harness now writes `status.json` and `dashboard.html` into each results directory so progress can be watched live instead of waiting for the final summary.
- Treat diff stats as "changes relative to the run's own freshly provisioned workspace" rather than "changes relative to the template folder on disk" so worktree metadata and line-ending drift do not pollute the measurement.
- After a run finishes, use `E:\agent_misc\benchmarks\analyze_benchmark_results.py` to derive a stable analysis layer with `analysis.json` plus `analysis.md`.
- The harness now persists conservative network-jitter fields into `result.json`, `summary.json/csv`, `status.json`, and the dashboard, while the analysis script can still recompute them from `stdout.log` for historical result directories.
- The analysis script now accepts repeated `--results-dir` or `--summary-file` inputs, so multiple benchmark result directories can be merged into one combined analysis output without hand-building a synthetic combined summary first.

## Starting Point

Use:

- task definitions in `E:\agent_misc\benchmarks\tasks.toml`
- harness in `E:\agent_misc\benchmarks\run_codex_benchmark.py`

Suggested first pass:

```powershell
python E:\agent_misc\benchmarks\run_codex_benchmark.py --list-tasks
python E:\agent_misc\benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --mode single_xhigh --mode subagents --repeat 1
python E:\agent_misc\benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --mode single_xhigh --mode subagents --repeat 2 --replicate-start 2
```

Backend examples:

```powershell
python E:\agent_misc\benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --workspace-backend copy --repeat 1
python E:\agent_misc\benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --workspace-backend git_worktree --baseline-ref HEAD --repeat 1
```

Use `--replicate-start` when you want a new results directory to continue an existing sequence cleanly as `r2`, `r3`, and so on, instead of reusing `r1`.

Dashboard:

```powershell
python E:\agent_misc\benchmarks\start_benchmark_dashboard.py --results-dir E:\agent_misc\benchmarks\results\<RUN_ID> --port 8010 --open-browser
```

When a run starts, the harness prints both the results directory and the generated `dashboard.html` path so you can point the viewer at the active benchmark before it finishes. Use `start_benchmark_dashboard.py` as the stable launcher: it prefers a fixed port, replaces an older benchmark dashboard already bound there, and writes fresh `dashboard_stdout.log` plus `dashboard_stderr.log` into the served results directory. The dashboard server itself exposes `/api/status` and `/api/stream` so the page can consume live SSE snapshots instead of repeatedly polling full text files. Those snapshots now carry incremental `full` or `append` text packets for prompt, final message, stdout, and validation panes, which keeps log pane scroll positions stable while also reducing repeated text transfer.

Post-run analysis:

```powershell
python E:\agent_misc\benchmarks\analyze_benchmark_results.py --results-dir E:\agent_misc\benchmarks\results\<RUN_ID> --print-markdown
python E:\agent_misc\benchmarks\analyze_benchmark_results.py --results-dir E:\agent_misc\benchmarks\results\<RUN_ID_1> --results-dir E:\agent_misc\benchmarks\results\<RUN_ID_2> --output-dir E:\agent_misc\benchmarks\results\<COMBINED_ANALYSIS_ID>
```
