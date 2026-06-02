---
id: codex-native-subagents
title: Codex Native Subagents
type: guide
workspace: subagent_lab
domains:
  - subagents
status: reference
created: 2026-03-19
updated: 2026-03-20
summary: Describe the native subagent roles, routing policy, and practical prompting patterns used in the nested workspace.
related:
  - root-mainline-plan
  - console-game-workload
supersedes: []
artifact_paths: []
---

# Codex Native Subagents

This guide explains the project-scoped native subagent setup in `subagent_lab`, including role boundaries, routing expectations, and when delegation is actually worth using.

## Index

- [Role Map](#role-map)
- [Entry Policy](#entry-policy)
- [Kickoff Pattern](#kickoff-pattern)
- [Practical Prompts](#practical-prompts)
- [Worker Tiering](#worker-tiering)
- [Legacy Files](#legacy-files)

This repo now supports native Codex subagents through project-scoped config:

- `E:\agent_misc\subagent_lab\.codex\config.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\explorer.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\worker_low.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\worker.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\worker_high.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\reviewer.toml`
- `E:\agent_misc\subagent_lab\.codex\agents\supervisor.toml`

## Role Map

- main Codex session: performs the first-pass framing and routing decisions
- `explorer`: read-heavy evidence gathering
- `worker_low`: low-complexity implementation
- `worker`: medium-complexity implementation
- `worker_high`: high-complexity implementation
- `reviewer`: bug and regression review
- `supervisor`: optional audit-only health gate, not in the default loop

Note:
- Codex already ships built-in `worker` and `explorer` agents.
- This repo no longer carries project-scoped `monitor` or `default` entry agents.
- Entry behavior is configured through the main session instructions for this workspace instead of a dedicated entry subagent.

## Entry Policy

This repo treats the main Codex session as the decision-maker for whether subagents are worth using.

Practical meaning:

- On ordinary low-complexity tasks, the root Codex session should usually just do the work directly.
- Spawn a child agent only when that delegation meaningfully reduces context noise or isolates a distinct kind of work.
- Avoid turning subagents into a mandatory pipeline.

## Kickoff Pattern

Start a normal Codex session in this repo and ask for the subagent workflow. You do not need to say `start with monitor`; the parent session should already behave that way.

Example:

```text
Use subagents only if they are actually helpful for this task.
For small, clear one-shot work, stay in the main agent.
For bigger or noisier work, decide whether to use `explorer`, a worker tier, and `reviewer`.
```

Shortest useful kickoff:

```text
Use subagents only if they are actually helpful for this task.
```

## Practical Prompts

Planning or diagnosis:

```text
If the root cause is not clear and the exploration would clutter the main thread, spawn `explorer` and come back with a narrow next round.
```

Implementation:

```text
If the implementation is large enough to benefit from isolation, choose the right worker tier for the change, then use `reviewer` when an independent diff read is worth the cost.
```

Review-only:

```text
Spawn `reviewer` on the latest change summary or diff.
```

## Worker Tiering

- `worker_low`: use for low-risk, local, mostly mechanical edits. Current default model: `gpt-5.4-mini`.
- `worker`: use for normal validated implementation rounds. Current model remains `gpt-5.3-codex`.
- `worker_high`: use for cross-file, stateful, or higher-risk changes. Current model: `gpt-5.4`.

The repo keeps `worker` as the middle tier for backward compatibility with existing prompts and benchmark comparisons.

Delegation policy:

- Do not delegate tiny one-shot changes just because a worker exists.
- Delegate when the implementation thread would otherwise flood the main agent with search output, shell logs, or iterative diff churn.
- Prefer fewer, higher-value subagent calls over a default assembly line.

Default routing rubric when delegation is actually useful:

- `worker_low`
  - expected shape: 1 file or 1-2 adjacent files
  - good fits: help text, local rendering tweak, deterministic output refinement, small test-only companion updates
  - avoid when: the round changes state rules, coupled behavior, or multi-mode output contracts
- `worker`
  - expected shape: a few related files and one bounded behavior change
  - good fits: ordinary feature slices, moderate CLI behavior changes, normal code-and-test coordination
  - avoid when: the round is clearly mechanical enough for `worker_low` or clearly stateful/cross-file enough for `worker_high`
- `worker_high`
  - expected shape: stateful or cross-file changes with meaningful regression risk
  - good fits: engine/models/UI/test coordination, output-contract changes across interactive and scripted modes, higher-risk gameplay logic changes
  - avoid when: the round can be narrowed into a cheaper lower-tier pass first

Escalation triggers for the main agent's delegation decision:

- expected changed files exceed the current tier
- the change touches persistent state or coupled gameplay rules
- the change affects multiple output modes or verification becomes non-trivial
- the round now needs tradeoff reasoning instead of straightforward execution

## Legacy Files

The earlier external orchestration prototype is still present in this repo:

- `E:\agent_misc\subagent_lab\legacy\codex.multiagent.toml`
- `E:\agent_misc\subagent_lab\legacy\codex.profiles.toml`
- `E:\agent_misc\subagent_lab\legacy\scripts\codex_multiagent_launcher.py`
- `E:\agent_misc\subagent_lab\legacy\scripts\launch-codex-multiagent.ps1`

Those files are legacy now. For Codex-native subagents, prefer the `.codex/` setup above.
