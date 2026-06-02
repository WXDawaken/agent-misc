# `reviewer` agent_type mismatch after desktop restart

## Summary

Observed a mismatch between Codex desktop and Codex CLI in the same root workspace `E:\agent_misc`.

- In the desktop app, `spawn_agent` with `agent_type="reviewer"` started working, then after a restart began failing with `unknown agent_type 'reviewer'`.
- In the CLI, `codex exec` from the same root could still successfully spawn a `reviewer`.
- A deliberately fake agent type in the CLI correctly failed, which suggests the CLI was genuinely resolving `reviewer` rather than silently falling back to `default`.

This makes the issue look more like a desktop/runtime bug than a workspace configuration problem in `E:\agent_misc`.

## Environment

- OS: Windows
- Shell: PowerShell 7.6.0
- Workspace root: `E:\agent_misc`
- Root guidance: neutral coordination workspace, not the main home for native subagent experiments

## Desktop Repro

Context: root workspace `E:\agent_misc`.

### Before restart

Using the desktop `spawn_agent` tool with:

- `agent_type: "reviewer"`
- minimal inherited conversation context

resulted in a successful child agent launch and a normal completion.

### After restart

Running the same kind of desktop `spawn_agent` call from the same root returned:

```text
unknown agent_type 'reviewer'
```

Using `agent_type: "default"` immediately afterward succeeded, so the child-agent path itself still worked.

## CLI Repro

From `E:\agent_misc`, run this minimal repro:

```powershell
@'
In workspace E:\agent_misc, do one minimal repro only. Attempt exactly one spawn_agent call with agent_type reviewer while keeping the child task isolated from the full parent conversation. Give it a tiny read-only task. Do not retry. If spawn_agent fails, report the exact error text.
'@ | codex exec -C E:\agent_misc --skip-git-repo-check --ephemeral --json --color never -s read-only
```

Observed result:

- CLI successfully spawned a child agent for `agent_type=reviewer`
- the child completed normally

## CLI Negative Control

Run the same shape of command, but replace `reviewer` with a fake type such as `reviewer_totally_fake_987`.

Observed result:

```text
unknown agent_type 'reviewer_totally_fake_987'
```

This negative control matters because it shows the CLI is not simply accepting arbitrary unknown types.

## Expected

- Desktop and CLI should agree on whether `reviewer` is a valid `agent_type` in the same workspace and same user environment.

## Actual

- Desktop after restart: `reviewer` rejected as unknown
- CLI from the same root: `reviewer` accepted
- CLI fake type: rejected as unknown

## Why this looks like a bug

- The same root workspace was used in both cases.
- The child-agent path itself remained healthy in desktop because `default` still worked.
- The CLI could still resolve `reviewer`.
- The CLI correctly rejected a fake type, so `reviewer` appears to be real and available there.

## Noise observed but likely unrelated

During CLI runs there were extra warnings, but they did not block the repro:

- plugin sync `403 Forbidden`
- PowerShell shell snapshot not supported
- `InvalidOperation: Cannot set property. Property setting is supported only on core types in this language mode.`

## Suggested issue title

Desktop `spawn_agent` rejects `agent_type="reviewer"` after restart, while `codex exec` in the same workspace still resolves it
