# Agent Experiment Lab

[中文](README.zh-CN.md) | English

Experimental tooling and fixtures for studying how coding agents behave across
prompt rendering, benchmark orchestration, subagent workflows, and interactive
text-game environments.

This repository is intentionally a lab, not a polished product. It keeps small,
inspectable tools close to the workloads they exercise so experiments can be
reproduced, reviewed, and adapted without a large service stack.

## What Is Here

- `benchmarks/`: benchmark runners, task definitions, workspace manifests,
  dashboard helpers, and judged-quality post-processing.
- `promptkit/`: a small stdlib-only prompt artifact renderer and linter for
  markdown plus front matter prompt files.
- `prompts/`: reusable prompt artifacts and example variable files.
- `OrbitLens/`: an agent-native 3D viewer MVP that lets 2D-vision agents inspect
  glTF/GLB scenes through controlled Three.js/Chromium renders.
- `playground/`: `Arcane Lab`, an original deterministic text RPG environment
  for testing long-horizon planning, tool use, and recovery behavior.
- `subagent_lab/`: native Codex subagent experiments and the `Salvage Run`
  console workload used by the benchmark harness.
- `docs/`: benchmark reports, design notes, and experiment memos that are meant
  to be shared with the repository.
- `tools/`: local helper scripts and generated indexes.

Some local workspace handoff files, run outputs, logs, caches, and sibling
checkouts are ignored by Git. In particular, `mail4agent` is treated as a
separate sibling repository rather than a submodule of this one.

## Codex Environment

This repository is primarily developed and exercised inside a Codex environment.
Several scripts assume the `codex` CLI is installed, authenticated, and available
on `PATH`. Pure Python utilities such as `promptkit` tests can run without
Codex, but benchmark runs, subagent experiments, and some runner scripts are
designed around Codex CLI behavior and local Codex configuration.

## Quick Start

Most tools are Python scripts with minimal dependencies. Use a recent Python 3
release from the repository root unless a command changes directories.

Run promptkit tests:

```powershell
python -m unittest promptkit.test_promptkit -v
```

Lint an example prompt artifact:

```powershell
python -m promptkit.render lint prompts\examples\arcane_lab_runner.prompt.md --vars prompts\examples\arcane_lab_runner.vars.json
```

List benchmark tasks:

```powershell
python benchmarks\run_codex_benchmark.py --list-tasks
```

Dry-run a benchmark invocation:

```powershell
python benchmarks\run_codex_benchmark.py --task small_scan_hazard_warning --mode single_xhigh --mode subagents --repeat 1 --dry-run
```

Run the `Salvage Run` workload tests:

```powershell
cd subagent_lab
python -m unittest test.test_salvage_run -v
```

Try the `Arcane Lab` text RPG smoke script:

```powershell
cd playground
python game.py --new --script scripts\smoke.txt
```

## Benchmark Shape

The benchmark harness compares different agent execution modes against the same
isolated tasks. Current tracks include:

- `single_xhigh`: one high-effort agent solves directly.
- `subagents`: a native subagent workflow solves with delegated roles.
- local-model code generation helpers for non-agentic patch attempts.

The harness records setup time, solve time, token usage, validation results,
changed-file summaries, and final messages. Separate helpers build blinded judge
packets and analyze judged quality after review.

Workspace materialization supports copy-based isolation and Git worktrees. Use
copy-based isolation for dirty local experiments and Git worktrees for clean,
commit-pinned baselines.

## Prompt Artifacts

`promptkit` is a deliberately small layer over markdown, front matter, and a
mustache-like template subset. It supports:

- declared inputs and simple type checks
- variable rendering
- list/object/truthy sections
- partial includes
- named variants
- rendered snapshots
- JSON IR compilation

It does not execute arbitrary expressions or shell commands. Keep complex
context assembly in Python or runner scripts, then render deterministic prompt
artifacts through promptkit.

## Safety Notes

This repository is for local agent experiments. It is not a security sandbox.
Agents and runners may execute code, write files, inspect workspace contents,
and produce large logs. Run untrusted agents only in isolated workspaces with
low-privilege credentials.

Do not commit secrets, provider tokens, generated agent workspaces, benchmark
results, save files, logs, local Codex homes, or sibling repository contents.
The root `.gitignore` is written to keep those out of normal Git operations,
but review changes before publishing.

## Publication Notes

The intended public layout is a single root repository for shared tooling and
fixtures:

- keep `subagent_lab/` as a normal tracked directory
- keep `mail4agent` as a sibling repository
- use Git worktrees only for temporary benchmark materialization, not as
  permanent repo structure
- keep local workspace handoff documents untracked

Before the first public commit, clean or archive temporary output directories
and decide whether any historical benchmark reports should move to a separate
results archive.
