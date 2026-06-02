# Source Policy Hardening Notes

Last updated: `2026-05-22`

## Current Implementation

Source policy is currently a benchmark compliance scanner, not a runtime hook.

Codex CLI runs now have a separate runner tool-policy hook layer. That layer is
not a source-policy implementation; where supported by Codex, it blocks
high-risk tool calls such as process termination, background process launches,
and destructive recursive deletes, then logs supported hook events to
`.runner\codex_hook_events.jsonl`. On the current Windows Codex CLI path,
`command_execution` does not emit these hooks, so `workspace-write` sandboxing is
the active command-execution control boundary. The working runner combination on
this host is `codex -a never exec --sandbox workspace-write` while keeping normal
Codex user config loaded; forcing `--ignore-user-config` caused Python helper
and workspace-write commands to be rejected by local policy during smoke tests.
Source-disclosure enforcement remains the scanner described below.

The policy has three layers:

- Prompt/reference policy: each track renders allowed and forbidden references
  into the shared prompt.
- Workspace packaging: `scripts\setup_agent_workspace.py` copies only the files
  intended for the selected track and workspace mode.
- Post-run scanning: runner summaries parse agent JSONL output and record source
  policy violations after the run.

The Python implementation lives in `scripts\runner_common.py`:

- `access_events_from_jsonl(...)` extracts command and tool-use inputs from
  runner JSONL output.
- `source_policy(...)` matches those inputs against forbidden source/data/script
  patterns.
- Track config can add `source_policy_extra_forbidden` patterns for
  environment-specific files such as Ledger Tower data.
- `build_track_summary(...)` writes the result into `.runner\summary.json`.

The older OpenCode Go PowerShell runner has a parallel implementation in
`scripts\run_opencode_go_playtest.ps1`.

## What It Catches

- Direct tool or command inputs that mention forbidden files such as `game.py`,
  `server.py`, `mcp_server.py`, `sdk\*.py`, `data\*.json`, smoke route files,
  or debug goals.
- Directory-listing attempts for sensitive paths when the command text contains
  the forbidden directory.
- Track-specific forbidden patterns supplied by `source_policy_extra_forbidden`.

Violations affect runner summaries and route-quality scoring. They do not
currently prevent the action from happening.

## Known Gaps

- It is not a syscall, filesystem, shell, or tool hook.
- It cannot reliably see file access performed inside a helper script if the
  forbidden path does not appear in the outer command or tool input.
- It is mostly post-run enforcement, so it detects violations after the sample.
- It intentionally ignores write/edit tool inputs to avoid false positives when
  agents write their own helper files.
- It currently scans tool and command inputs more reliably than tool outputs, so
  a broad workspace glob can reveal forbidden paths without being counted when
  the input is only a broad pattern such as `*`.
- It cannot detect SDK-object internal data inspection, such as reading an
  in-memory `tower.data` field, when no forbidden file path appears in the
  outer command or tool input.
- It does not classify the contents of helper scripts written under `logs\`
  unless the outer command mentions forbidden paths; a helper can import SDK
  internals or dump map-derived structures without producing a scanner hit.
- Default patterns still carry Arcane Lab historical assumptions; Ledger Tower
  currently relies on extra track patterns for its environment-specific data.
- It can produce false positives when an agent mentions a forbidden path in a
  report rather than reading it.

## Hardening Directions

Possible follow-up work:

- Evaluate a dedicated Playground `CODEX_HOME` for Codex CLI playtest runs so
  temporary `agent_workspaces\...` trust entries do not accumulate in the user's
  global `~\.codex\config.toml`. The design to test later is a persistent
  `playground\.codex_home` outside the generated agent workspace, with runner
  environment `CODEX_HOME` pointing there and a conservative scrubber that
  removes only `[projects.*]` entries for temporary playtest workspaces. Do not
  use a per-run copied `auth.json`; smoke testing an old benchmark-scoped
  `CODEX_HOME` hit `refresh_token_reused`, so auth rotation can be broken by
  cloning ChatGPT login state. Do not switch to `--ignore-user-config` as a
  workaround; current Windows sandbox smokes showed that combination rejects
  Python helpers and workspace writes.
- Add a pre-tool deny layer in each runner that rejects forbidden read/list
  commands before execution.
- Extend the Codex CLI hook policy from process-safety commands to optional
  source-boundary commands once false positives are understood for each track.
- Wrap shell execution with a policy-aware command parser for common file-read,
  list, glob, and Python invocation patterns.
- Add a controlled Python helper runner that can instrument or restrict file
  opens for official benchmark helpers.
- Use filesystem sandboxing or per-run manifests when the runner supports it.
- Normalize source policy around environment ids so default forbidden files are
  generated from track/workspace metadata rather than Arcane-specific defaults.
- Record both attempted access and confirmed access when runner/tool telemetry
  makes that distinction available.
- Scan tool outputs for forbidden path disclosures, especially glob/list output,
  and consider treating broad root globs as attempted access when the track
  forbids discovering implementation or data files.
- Optionally scan helper-script contents under allowed write directories for
  imports or attribute access patterns that cross the declared disclosure
  boundary.

## Intended Semantics

Source policy should remain separate from game scoring. Server verification
decides whether the game attempt is accepted. Source policy decides whether the
agent respected the benchmark's disclosure boundary and should be used in
quality scoring, audit notes, and benchmark filtering.
