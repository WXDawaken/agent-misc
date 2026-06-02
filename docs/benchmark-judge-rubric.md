---
id: benchmark-judge-rubric
title: Benchmark Judge Rubric
type: rubric
workspace: root
domains:
  - benchmark
  - judge
status: reference
created: 2026-03-19
updated: 2026-03-19
summary: Score completed benchmark artifacts on correctness, scope control, code quality, and evidence quality.
related:
  - subagent-benchmark-plan
supersedes: []
artifact_paths: []
---

# Benchmark Judge Rubric

Use this rubric during blinded review passes so benchmark quality judgments stay consistent across runs and modes.

## Index

- [Correctness](#correctness)
- [Scope Control](#scope-control)
- [Code Quality](#code-quality)
- [Evidence Quality](#evidence-quality)
- [Notes](#notes)

Score each completed run on a 1-5 scale.

## Correctness

- `5`: fully satisfies the task and acceptance criteria
- `3`: mostly correct with minor gaps
- `1`: major task failure or wrong behavior

## Scope Control

- `5`: narrow change, no unnecessary surface area
- `3`: some extra churn but still acceptable
- `1`: obvious scope drift or unrelated edits

## Code Quality

- `5`: clear implementation, coherent tests, maintainable
- `3`: workable but awkward or brittle
- `1`: poor structure or weak validation

## Evidence Quality

- `5`: final message cites concrete validation and changed surfaces
- `3`: some evidence, but incomplete
- `1`: weak or unsupported completion claim

## Notes

- Judge artifacts, not solve cost.
- If possible, hide whether the run came from `subagents` or `single_xhigh`.
- Keep final notes short and concrete.
