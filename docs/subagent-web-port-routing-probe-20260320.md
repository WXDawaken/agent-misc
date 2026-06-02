# Web Port Routing Probe 2026-03-20

## Goal

Record CLI experiments against the `Salvage Run` web-port workload and evaluate how willing the main agent is to use subagents when the workload grows from shared-core refactoring into a local web shell and later incident-style diagnosis rounds.

This note is root-level on purpose:

- it is a benchmark-style conclusion, not a project-scoped workload doc
- it compares routing behavior across multiple disposable experiment runs
- it also proposes the next higher-pressure routing test

## Common Run Setup

All three rounds were run through Codex CLI in disposable workspaces under `E:\agent_misc\.tmp_test`.

Common CLI shape:

- tool: `codex exec`
- model: `gpt-5.4`
- reasoning effort: `medium`
- sandbox: `workspace-write`
- approval policy override: `never`
- session persistence: `--ephemeral`
- output capture: `--json` plus `--output-last-message`

Each round explicitly asked the main agent to:

- use the repo's main-agent routing workflow
- use subagents only if they were actually helpful
- report in the final message whether subagents were used and why

## Round 1

### Intent

Implement Milestone 1 of the web-port plan:

- extract a deterministic serializable snapshot contract from the console game
- add tests
- update docs

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round1_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round1_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round1_20260320_events.jsonl`

### Observed Routing

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- treated the round as a bounded shared-core extraction inside a small Python surface
- decided that review/merge overhead would exceed any context-isolation benefit

### Outcome

- implemented the snapshot contract locally
- kept the Python simulation as the source of truth
- added coverage in `test.test_salvage_run`

Validation:

- `python -m unittest test.test_salvage_run -v`
- reported pass: `28/28` tests

Usage:

- `input_tokens = 532860`
- `cached_input_tokens = 484352`
- `output_tokens = 11807`

## Round 2

### Intent

Implement Milestone 2 as a minimal local web-shell vertical slice:

- local standard-library web server
- browser shell
- command submission path
- tests and docs

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round2_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round2_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round2_20260320_events.jsonl`

### Observed Routing

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- classified the round as one runtime seam, one local server, one static UI, and focused tests
- still considered that a bounded single-agent slice

### Outcome

- built a local server under `salvage_run_web/`
- added browser assets under `web/`
- added `test.test_salvage_run_web`
- updated run docs for the web shell

Validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- reported pass on both suites

Usage:

- `input_tokens = 701808`
- `cached_input_tokens = 631808`
- `output_tokens = 15333`

## Round 3

### Intent

Probe whether an explicit task list would change routing behavior.

The round gave the main agent three tasks:

1. backend control contract
2. frontend control/help panel
3. integration, tests, and docs

The prompt explicitly allowed parallel or sequential execution and highlighted that tasks 1 and 2 could be parallelized if useful.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round3_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round3_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round3_20260320_events.jsonl`

### Observed Routing

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- backend payload shape and frontend rendering/key handling were still tightly coupled
- tasks 1 and 2 were done sequentially
- validation was effectively parallelized only at the end

### Outcome

- added a structured server-owned controls manifest
- moved the browser help/control panel to server-driven metadata
- updated web tests and docs

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `python -m unittest test.test_salvage_run -v`
- reported pass on both suites

Usage:

- `input_tokens = 623721`
- `cached_input_tokens = 572928`
- `output_tokens = 10820`

## Round 4

### Intent

Run the first delegation-pressure round:

- start a narrow replay slice for Milestone 3
- keep backend and frontend ownership cleaner
- require an independent review pass before completion

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round4_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round4_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round4_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 3`
- `wait = 1`
- `close_agent = 2`

Observed delegation pattern:

- one initial worker spawn attempt failed because the session could not fork thread context in that form
- one worker subagent was then launched successfully for the isolated frontend replay-panel slice
- one independent reviewer subagent was launched after implementation, as required by the prompt

Main-agent rationale:

- backend replay state, endpoint work, tests, and docs stayed on the main thread
- frontend replay-panel work was delegated because its three `web/` files formed a clean bounded sidecar slice
- independent review was treated as a real gate, not a ceremonial summary

### Outcome

- the backend gained replay-session state and replay-step endpoint support
- the frontend gained a replay side panel driven by server-owned metadata
- the reviewer found two concrete defects before finalization:
  - parity metadata was effectively hardcoded
  - JSON booleans were being accepted as replay-step integers
- the main thread fixed both issues before completion

Validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- `node --check web/app.js`
- reported pass on all three checks

Usage:

- `input_tokens = 2215163`
- `cached_input_tokens = 1900672`
- `output_tokens = 20822`

## Round 5

### Intent

Remove the mandatory-review pressure and test whether cleaner ownership alone is enough to keep delegation alive.

The round asked for:

- backend replay export polish
- frontend replay timeline panel improvements
- parity/docs updates

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round5_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round5_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round5_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 2`
- `wait = 0`
- `close_agent = 1`

Observed delegation pattern:

- one initial worker spawn attempt failed because context forking was not available in that form
- one worker subagent then launched successfully for the backend replay-contract slice
- no independent reviewer was used

Main-agent rationale:

- clean ownership was now sufficient to justify one worker even without a forced review gate
- the main thread kept the frontend replay timeline panel, console parity extension, docs, and integration

### Outcome

- backend replay metadata gained richer navigation groups and timeline entries/markers
- frontend replay UI gained grouped navigation and a clickable timeline from server-owned metadata
- parity/docs were extended locally on the main thread

Validation:

- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- reported pass on both suites

Usage:

- `input_tokens = 1123412`
- `cached_input_tokens = 1071744`
- `output_tokens = 11972`

## Round 6

### Intent

Test whether the main agent will scale beyond one worker when two implementation slices have especially explicit ownership.

The round asked for:

- backend replay annotation/filter contract
- frontend replay filter and legend panel
- parity/docs/integration on the main thread

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round6_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round6_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round6_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 4`
- `wait = 3`
- `close_agent = 0`

Observed delegation pattern:

- two initial spawn attempts failed because context forking was unavailable in that form
- two worker subagents then launched successfully:
  - one for the backend annotation/filter contract
  - one for the frontend replay filter/legend panel
- no independent reviewer was used

Main-agent rationale:

- backend and frontend ownership lines were clean enough that two workers were likely useful
- the main thread kept integration, parity/docs, and final validation

### Outcome

- backend replay metadata gained server-owned annotations plus a deterministic filter manifest
- frontend replay UI gained a filter panel and legend driven by the server contract
- the main thread performed a small integration edit so the UI stopped inferring categories and used the explicit server manifest

Validation:

- `node --check web/app.js`
- `python -m unittest test.test_salvage_run -v`
- `python -m unittest test.test_salvage_run_web -v`
- reported pass on all three checks

Usage:

- `input_tokens = 985609`
- `cached_input_tokens = 932096`
- `output_tokens = 9238`

## Round 7

### Intent

Probe the `explorer` threshold with a symptom-driven diagnosis round instead of an explicit implementation brief.

The prompt described only the observed symptom:

- a quit-based replay could show a false parity diff until the replay reached the end step

The prompt explicitly allowed `explorer` if root-cause discovery would otherwise clutter the main thread.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round7_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round7_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round7_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- kept the fix local because the root cause became clear after a short trace
- considered the change bounded enough that neither `explorer` nor `reviewer` would reduce noise

### Outcome

- diagnosed the bug as client-side
- removed the browser-side override of `matches_console`
- made the parity line explicitly server-owned
- added a regression assertion that parity stays stable when stepping away from the final replay frame

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `python -m unittest test.test_salvage_run -v`
- reported pass on both suites

Usage:

- `input_tokens = 230143`
- `cached_input_tokens = 202752`
- `output_tokens = 3390`

## Round 8

### Intent

Probe the `explorer` threshold again with a broader cross-surface replay incident.

The prompt described multiple inconsistent signals at once:

- replay panel status or summary text could disagree with timeline cues
- timeline markers or annotations could appear to shift with the selected replay step
- parity could disagree with the final replay-versus-console relationship before the replay reached the end

The prompt explicitly allowed `explorer` if comparing backend, frontend, and parity-contract causes would otherwise clutter the main thread.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round8_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round8_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round8_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- kept the incident local because it judged the fault to be confined to one Python replay payload builder plus one browser render path
- considered delegation higher-overhead than directly correlating the drift across those two surfaces

### Outcome

- restored server-owned replay summary rendering in the browser
- anchored terminal parity to the replay final state instead of the selected frame
- removed step-dependent replay annotation and marker drift
- added focused replay regression coverage

Validation:

- `python -m unittest test.test_salvage_run_web test.test_salvage_run -v`
- reported pass after one local regression-test adjustment

Usage:

- `input_tokens = 861822`
- `cached_input_tokens = 777984`
- `output_tokens = 11201`

## Round 9

### Intent

Test whether a two-symptom incident with unclear coupling is enough to trigger diagnosis delegation.

The prompt described a replay filter incident cluster:

- replay filter badges, legend entries, or available categories could change while stepping through the same replay
- hidden replay filter categories could reappear after replay navigation or reset
- it was not obvious whether the symptoms shared one cause or required two narrow fixes

The prompt explicitly allowed `explorer` if comparing Python replay contracts, browser replay state, and tests would otherwise clutter the main thread.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round9_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round9_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round9_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 0`
- `wait = 0`
- `close_agent = 0`

Main-agent rationale:

- stayed local because it judged the replay diagnosis small enough to correlate directly across the Python payload builder, browser state, and tests
- decided that the incident cluster did not justify explorer, worker, or reviewer overhead

### Outcome

- diagnosed the symptoms as one incident cluster with two narrow fixes
- restored a replay-wide server-owned filter manifest instead of a step-local one
- preserved user-chosen replay filter visibility across manifest rebuilds
- added focused regression coverage in both Python and JavaScript tests

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- reported pass on both checks

Usage:

- `input_tokens = 652747`
- `cached_input_tokens = 620672`
- `output_tokens = 7759`

## Round 10

### Intent

Run the first explicit regression-origin audit round:

- make the main agent inspect sibling disposable rounds for likely regression origin
- keep the current-workspace fix narrow and replay-focused
- allow `explorer` specifically for historical search or artifact comparison work

The prompt pointed the main agent at sibling rounds 5 through 9 under `E:\agent_misc\.tmp_test` and asked it to identify the earliest likely bad round or narrowest plausible introduction window before fixing only the current workspace.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round10_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round10_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round10_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 2`
- `wait = 2`
- `close_agent = 0`

Observed delegation pattern:

- one initial `explorer` spawn attempt failed because the thread could not be forked in that session form
- one `explorer` sidecar then launched successfully without forked context for sibling-round audit
- the main thread continued local diagnosis and implementation while the sidecar audited round history
- the main thread stopped waiting on the sidecar once it was no longer useful on the critical path

Main-agent rationale:

- history search across sibling disposable rounds was a clean enough side task to justify delegation
- the current-workspace replay fix still stayed local because it was bounded to one Python replay payload builder plus one browser visibility-preservation path
- once the sidecar lagged behind the critical path, the main thread preferred direct local comparison of rounds 8 through 10 instead of blocking on the sidecar result

### Outcome

- fixed a replay regression cluster in two places:
  - replay-wide `filter_manifest` had drifted back to step-local behavior
  - `terminal_parity` had been recomputed from the selected replay frame
  - browser filter visibility had been reset during manifest rebuilds
- restored replay-wide server-owned filter metadata and cached final-state parity in Python
- restored preservation of user-selected filter visibility in the browser
- added focused regression coverage in Python and JavaScript tests
- concluded that the likely introduction window was `round9 -> round10`, with `round10` as the earliest likely bad round for the exact observed symptom cluster

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- `python -m unittest test.test_salvage_run test.test_salvage_run_web -v`
- reported pass on all three checks

Usage:

- `input_tokens = 961805`
- `cached_input_tokens = 894080`
- `output_tokens = 7810`

## Round 11

### Intent

Run the first gated historical-evidence round:

- require a concise evidence table covering sibling rounds before closeout
- allow `explorer` for read-only history audit work
- observe whether the sidecar result is merely spawned or actually incorporated into the final answer

The prompt explicitly required a table covering at least three sibling rounds plus the current workspace, with concrete file-level or artifact-level evidence.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round11_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round11_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round11_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 2`
- `close_agent = 0`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit
- the main thread fixed the current workspace locally while the sidecar gathered read-only history evidence
- the main thread waited twice for the sidecar and received a usable audit on the second wait
- the final evidence table explicitly incorporated the sidecar output for rounds 7 through 10

Main-agent rationale:

- sibling-round comparison would have added noise to the main thread, so it was worth offloading
- the current-workspace replay fix still stayed local because it was a bounded Python replay payload plus browser visibility-state correction
- the sidecar became useful because the evidence table was a real completion gate rather than an optional supplement

### Outcome

- fixed the replay regression cluster in the current workspace:
  - replay-wide `filter_manifest` had been recomputed from the current frame
  - `terminal_parity` had been recomputed from the current frame
  - browser replay filter visibility had been reset on rerender
- restored replay-wide cached metadata in Python
- restored preservation of existing replay filter visibility in JavaScript
- added focused regression coverage for replay-wide manifest/parity stability at intermediate steps
- produced a sidecar-informed evidence table covering `round7` through `round11`
- concluded that the likely introduction window remained `round9 -> round10`, with `round10` as the earliest likely fully bad round

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- reported pass on both checks

Usage:

- `input_tokens = 403993`
- `cached_input_tokens = 347392`
- `output_tokens = 5067`

## Round 12

### Intent

Run the first combined audit-plus-optional-review round:

- keep the historical evidence table gate from round 11
- make the local fix contract-sensitive around replay summary and step-label semantics
- explicitly allow but do not require independent review

The prompt asked for a narrow replay-contract fix touching both Python-owned replay payload text semantics and browser-side replay text rendering.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round12_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round12_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round12_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 2`
- `wait = 1`
- `close_agent = 2`

Observed delegation pattern:

- one initial explorer spawn attempt failed in its first session form
- one `explorer` sidecar then launched successfully for sibling-round audit
- one `reviewer` subagent launched successfully for the narrow replay-contract fix
- the main thread implemented the fix locally, used the sidecar audit for the evidence table, and used the reviewer for a final risk check

Main-agent rationale:

- the sibling-round comparison still fit clean `explorer` ownership
- the current-workspace fix stayed local because it was small, but it was contract-sensitive enough that an optional reviewer became worth the overhead
- reviewer output was used as a risk check, not as a blocker that forced code changes

### Outcome

- fixed a contract-sensitive replay regression in the current workspace:
  - Python had degraded the replay summary to generic navigation text
  - Python had degraded `replay.step.label` to a raw numeric string
  - the browser had inverted replay summary precedence and let numeric fallback beat server labels
- restored Python as the source of truth for authored replay summary plus `Start` / `Step N` / `End` step-label semantics
- restored browser precedence so `replay.summary` and `step.label` win before fallbacks
- added focused regression coverage in Python and JavaScript tests
- explorer-backed audit concluded that surviving-source regression first appeared in `round12`, while `round8` only showed transient artifact evidence of a similar pre-fix bug
- reviewer found no blocking defect and only noted a non-blocking single-frame `Start` vs `End` edge case

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `python -m unittest test.test_salvage_run -v`
- `node test\test_web_app_replay_filters.js`
- reported pass on all three checks

Usage:

- `input_tokens = 1183490`
- `cached_input_tokens = 1108480`
- `output_tokens = 9239`

## Round 13

### Intent

Run the first audit-without-reviewer-hint round:

- keep the historical evidence table gate from round 12
- keep the local fix narrow and contract-sensitive around replay summary and step-label semantics
- remove any explicit statement that optional review would be a reasonable choice

The prompt still allowed `explorer` for sibling-round audit work, but it did not mention `reviewer` at all.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round13_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round13_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round13_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 1`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 9 through 12
- no `reviewer` subagent was launched
- the main thread waited for the explorer result, used it in the final evidence table, and handled implementation plus validation locally

Main-agent rationale:

- historical comparison across sibling disposable rounds still fit clean `explorer` ownership
- the current-workspace fix stayed small enough that the agent kept it local
- removing the review hint was enough to eliminate reviewer usage on this otherwise similar contract-sensitive round

### Outcome

- fixed the replay text-contract regression in the current workspace:
  - Python had collapsed `replay.summary` to generic navigation text
  - Python had degraded `replay.step.label` to a numeric string
  - the browser had inverted replay summary precedence and let numeric fallback beat server-authored labels
- restored Python as the source of truth for authored replay summary plus `Start` / `Step N` / `End` step-label semantics
- restored browser precedence so `replay.summary` and `step.label` win before navigation or numeric fallbacks
- explorer-backed audit concluded that rounds 9 through 11 were clean in surviving source/tests, while round 12 had only mixed artifact evidence of the same bug cluster

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- `python -m unittest test.test_salvage_run_web.SalvageRunWebTests.test_http_server_serves_state_and_processes_commands -v`
- reported pass on all three checks

Usage:

- `input_tokens = 501723`
- `cached_input_tokens = 447232`
- `output_tokens = 6286`

## Round 14

### Intent

Run the first broader no-reviewer-hint replay-contract round:

- keep the historical evidence table gate from rounds 12 and 13
- keep reviewer entirely unmentioned in the prompt
- broaden the current-workspace risk surface from summary and step text into parity wording and browser fallback precedence

The goal was to test whether a wider local replay-contract fix would make reviewer appear even without any prompt framing in favor of review.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round14_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round14_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round14_20260320_events.jsonl`

Operational note:

- the first sandboxed `codex exec` attempt failed on certificate-store and transport access
- the successful run was completed after rerunning outside the sandbox to restore API connectivity

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 1`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 10 through 13
- no `reviewer` subagent was launched
- the main thread waited for the explorer result, used it in the final evidence table, and handled implementation plus validation locally

Main-agent rationale:

- historical comparison across sibling disposable rounds still fit clean `explorer` ownership
- even after broadening the local regression bundle, the agent still judged the implementation slice small enough to keep local
- increasing replay-contract risk inside the current workspace alone was not enough to reintroduce reviewer without a prompt hint

### Outcome

- fixed the broader replay text-contract regression in the current workspace:
  - Python had collapsed `replay.summary` to generic navigation text
  - Python had degraded `replay.step.label` to a numeric string
  - Python had weakened `terminal_parity.line` by removing the leading `Matches console` / `Differs from console` prefix
  - the browser had inverted replay summary precedence, preferred numeric step fallback, and preferred weaker parity wording over server-owned text
- restored Python as the source of truth for authored replay summary, semantic step labels, and parity line wording
- restored browser precedence so `replay.summary`, `step.label`, and parity `line` win before local fallback text
- updated focused JavaScript regression coverage to pin parity-line behavior alongside summary precedence
- explorer-backed audit concluded that rounds 12 and 13 were healthy, while rounds 10 and 11 only showed the older step-label weakness rather than the full regression bundle

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `python -m unittest test.test_salvage_run -v`
- `node test\test_web_app_replay_filters.js`
- reported pass on all three checks

Usage:

- `input_tokens = 681713`
- `cached_input_tokens = 615680`
- `output_tokens = 6766`

## Round 15

### Intent

Run the first worker-plus-integration no-reviewer-hint round:

- keep the historical evidence table gate from rounds 13 and 14
- keep reviewer entirely unmentioned in the prompt
- explicitly call out a clean browser-side ownership boundary that could be delegated to a worker

The goal was to test whether making worker ownership more obvious would cause the main thread to use both an `explorer` sidecar and an implementation worker, and whether reviewer would then appear during integration.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round15_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round15_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round15_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 0`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 11 through 14
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread used the sidecar only for history audit and still handled implementation plus validation locally

Main-agent rationale:

- historical comparison across sibling rounds remained a clean `explorer` task
- even with an explicit browser-side ownership hint, the implementation slice still looked small and coupled enough that the agent chose not to delegate it
- the hint alone was not sufficient to push implementation routing from local execution into worker delegation

### Outcome

- fixed the split replay text-contract regression in the current workspace:
  - Python had collapsed `replay.summary` to navigation text
  - Python had degraded `replay.step.label` to numeric output
  - Python had weakened `terminal_parity.line` by dropping the leading `Matches console` / `Differs from console` wording
  - the browser had preferred navigation summary, numeric-first step rendering, and weaker parity wording over server-owned text
- restored Python as the source of truth for replay summary, step-label semantics, and parity line wording
- restored browser precedence so `replay.summary`, `step.label`, and parity `line` win before fallback text
- tightened the focused JS harness to keep summary ordering and parity fallback behavior pinned
- explorer-backed audit concluded that round 11 only showed the older step-label weakness, while rounds 12 through 14 remained healthy

Validation:

- `node test/test_web_app_replay_filters.js`
- `python -m unittest test.test_salvage_run_web -v`
- reported pass on both checks

Usage:

- `input_tokens = 692333`
- `cached_input_tokens = 630144`
- `output_tokens = 6185`

## Round 16

### Intent

Run the first expanded browser worker-boundary round:

- keep the historical evidence table gate from rounds 14 and 15
- keep reviewer entirely unmentioned in the prompt
- enlarge the browser-side ownership block from one JS file to a fuller replay-inspector slice spanning template, styles, browser logic, and focused browser tests

The goal was to test whether a materially larger browser/UI ownership block would finally cross the worker threshold without any reviewer hint.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round16_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round16_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round16_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 1`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 12 through 15
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread used the sidecar only for history audit and still handled implementation plus validation locally

Main-agent rationale:

- historical comparison across sibling rounds remained a clean `explorer` task
- even with a larger browser-side ownership block, the implementation still looked locally tractable enough that the agent chose not to delegate it
- enlarging the browser slice was still not sufficient to push this replay-inspector workload over the worker threshold

### Outcome

- fixed the broader replay-contract and replay-inspector regression in the current workspace:
  - Python had collapsed `replay.summary` to navigation text
  - Python had degraded `replay.step.label` to numeric output
  - Python had weakened `terminal_parity.line` by dropping the leading `Matches console` / `Differs from console` wording
  - the browser had preferred navigation summary and weaker parity wording over server-owned text
  - the replay inspector template and styles had weakened summary/parity emphasis and collapsed the filter/legend card structure
- restored Python as the source of truth for replay summary, step-label semantics, and parity line wording
- restored browser precedence so `replay.summary`, `step.label`, and parity `line` win before fallback text
- restored the emphasized replay summary/parity presentation and card-based replay-inspector shell
- tightened focused browser regression coverage, including a new replay-shell markup test
- explorer-backed audit concluded that rounds 12 through 15 did not show the full broad browser-inspector regression bundle, though some weaker browser fallback/emphasis issues predated the current round

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- `node test\test_web_replay_shell_markup.js`
- reported pass on all three checks

Usage:

- `input_tokens = 1056602`
- `cached_input_tokens = 980224`
- `output_tokens = 7266`

## Round 17

### Intent

Run the first dual-disjoint-workers round:

- keep the historical evidence table gate from rounds 15 and 16
- keep reviewer entirely unmentioned in the prompt
- present two genuinely separate implementation blocks: a Python replay-contract block and a browser replay-inspector block

The goal was to test whether the main agent would finally pay coordination cost once the current round contained two plausibly parallel implementation tracks instead of just one larger browser-side slice.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round17_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round17_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round17_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 1`

Observed delegation pattern:

- one initial `explorer` spawn attempt failed before a second attempt succeeded
- one `explorer` sidecar launched successfully for sibling-round audit over rounds 13 through 16
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread used the sidecar only for history audit and still handled implementation plus validation locally

Main-agent rationale:

- historical comparison across sibling rounds remained a clean `explorer` task
- even with two disjoint implementation blocks available, the agent still judged the current round locally tractable enough to avoid coordination overhead
- prompt-level decomposition into Python-side and browser-side ownership blocks was still weaker than the agent's own compression strategy

### Outcome

- fixed the dual-surface replay regression in the current workspace:
  - Python had collapsed `replay.summary` to navigation text
  - Python had degraded `replay.step.label` to numeric output
  - Python had weakened `terminal_parity.line` by dropping the leading `Matches console` / `Differs from console` wording
  - the replay-step HTTP endpoint had regressed to accept boolean values as integers
  - the browser had preferred navigation summary and weaker parity wording over server-owned text
  - the replay inspector template and styles had weakened summary/parity emphasis and collapsed the filter/legend card structure
- restored Python as the source of truth for replay summary, step-label semantics, parity line wording, and boolean step validation
- restored browser precedence so `replay.summary`, `step.label`, and parity `line` win before fallback text
- restored the emphasized replay summary/parity presentation and card-based replay-inspector shell
- tightened focused Python and browser regression coverage
- explorer-backed audit concluded that the full dual-surface regression bundle was not present in rounds 13 through 16, though a weaker latent browser step-fallback issue likely began in round 15 and persisted into round 16

Validation:

- `python -m unittest test.test_salvage_run_web -v`
- `node test\test_web_app_replay_filters.js`
- `node test\test_web_replay_shell_markup.js`
- reported pass on all three checks

Usage:

- `input_tokens = 742995`
- `cached_input_tokens = 677376`
- `output_tokens = 8557`

## Round 18

### Intent

Run the first heavier dual-workers round:

- keep the historical evidence table gate from rounds 16 and 17
- keep reviewer entirely unmentioned in the prompt
- make both the Python-side and browser-side implementation blocks materially heavier by adding extra acceptance surfaces on each side

The goal was to test whether the main agent would finally pay coordination cost once both implementation blocks were disjoint and each carried more substantial validation weight.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round18_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round18_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round18_20260320_events.jsonl`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 0`
- `close_agent = 0`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 14 through 17
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread still handled implementation plus validation locally
- unlike several earlier audit rounds, the successful event log for this round does not show an explicit completed `wait` or `close_agent`; the final answer still incorporated the audit result

Main-agent rationale:

- historical comparison across sibling rounds remained a clean `explorer` task
- even after making both implementation blocks heavier and adding extra acceptance surfaces, the agent still judged the round locally tractable enough to avoid coordination overhead
- at this point, prompt-level decomposition and extra acceptance weight both remain weaker than the agent's own compression strategy inside this replay-contract workload family

### Outcome

- fixed the heavier dual-surface replay regression in the current workspace:
  - Python had collapsed `replay.summary` to navigation text
  - Python had degraded `replay.step.label` to numeric output
  - Python had weakened `terminal_parity.line` by dropping the leading `Matches console` / `Differs from console` wording
  - the replay-step HTTP endpoint had regressed to accept boolean values as integers
  - the browser had preferred navigation summary and weaker parity wording over server-owned text
  - the replay inspector had weakened summary/parity emphasis and collapsed the filter/legend card structure
- restored Python as the source of truth for replay summary, step-label semantics, parity line wording, and boolean step validation
- restored browser precedence so `replay.summary`, `step.label`, and parity `line` win before fallback text
- restored the stronger replay inspector shell and emphasis styling
- tightened focused Python and browser regression coverage, including the new replay payload contract test and replay inspector copy test
- explorer-backed audit concluded that rounds 14 through 17 mostly preserved the stronger replay behavior, so the full heavy dual-surface regression bundle appears specific to the current disposable round rather than clearly originating in those siblings

Validation:

- `python -m unittest test.test_replay_payload_contract test.test_salvage_run_web`
- `node test/test_web_app_replay_filters.js`
- `node test/test_web_replay_shell_markup.js`
- `node test/test_web_replay_inspector_copy.js`
- reported pass on all four checks

Usage:

- `input_tokens = 1373061`
- `cached_input_tokens = 1291264`
- `output_tokens = 8761`

## Round 19

### Intent

Run the first cross-feature parallel round after replay-only slices stopped producing worker delegation:

- keep a required sibling-round evidence table over rounds 16 through 18
- keep reviewer entirely unmentioned in the prompt
- split the current workspace into two qualitatively different implementation surfaces:
  - control-manifest/runtime contract work
  - replay-inspector/browser contract work

The goal was to test whether a genuinely cross-feature repair round would finally look expensive enough to justify implementation workers.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round19_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round19_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round19_20260320_events.jsonl`

### Model / Runtime

- `model = gpt-5.4`
- `reasoning effort = medium`
- `sandbox = workspace-write`
- `approval_policy = never`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 2`
- `close_agent = 1`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round audit over rounds 16 through 18
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread still handled both implementation surfaces locally
- the main thread waited for the sidecar, but when no usable evidence arrived in time it completed the sibling-round comparison locally and closed the sidecar afterward

Main-agent rationale:

- historical artifact comparison still looked like a clean `explorer` sidecar
- even with two qualitatively different feature areas, the actual repair work still looked locally tractable enough to compress into one implementation pass
- when the sidecar lagged, the main thread preferred direct fallback over paying more coordination cost or blocking the critical path

### Outcome

- fixed the cross-feature control-manifest drift in the current workspace:
  - restored `HELP_TEXT` as the control summary
  - restored the `dash d` raw-command placeholder
  - restored Arrow Right hints/triggers for `d`
  - restored terminal-safe `help`
- fixed the cross-feature browser replay-inspector drift in the current workspace:
  - restored replay-summary precedence in `web/app.js`
  - restored the expected summary/parity classes and inspector headings in `web/index.html`
  - restored the two-column replay card layout plus summary/parity accent styling in `web/styles.css`
- also patched `salvage_run_web/app.py` so `/api/reset` consumes reset POST JSON before resetting; the agent treated this as adjacent failing-path stabilization rather than as a separate delegation boundary
- produced a file-level evidence table showing the seeded cross-feature drift is absent in rounds 17 and 18, while round 16 only differs by an older parity-tint variant
- concluded the narrowest plausible introduction window for the seeded drift is between rounds 18 and 19

Validation:

- `python -m unittest test.test_control_manifest_contract test.test_salvage_run_web -v`
- `node test/test_web_app_replay_filters.js`
- `node test/test_web_replay_shell_markup.js`
- `node test/test_web_replay_inspector_copy.js`
- reported pass on all four checks

Usage:

- `input_tokens = 1091313`
- `cached_input_tokens = 981888`
- `output_tokens = 18320`

## Round 20

### Intent

Run the first cross-feature forward-feature round instead of another shallow repair:

- keep a required sibling-round evidence table over rounds 17 through 19
- keep reviewer entirely unmentioned in the prompt
- split the current workspace into two forward-looking feature slices:
  - runtime/control-manifest quick-reference and terminal-affordance delivery
  - browser replay-overview visibility and filter-status delivery

The goal was to test whether a deeper feature-construction round, rather than another restoration pass, would finally look expensive enough to justify implementation workers.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round20_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round20_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round20_20260320_events.jsonl`

### Model / Runtime

- `model = gpt-5.4`
- `reasoning effort = medium`
- `sandbox = workspace-write`
- `approval_policy = never`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- `wait = 1`
- `close_agent = 1`

Observed delegation pattern:

- one `explorer` sidecar launched successfully for sibling-round evidence over rounds 17 through 19
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread still handled all feature delivery and validation locally
- unlike round 19, the main thread explicitly waited for the sidecar result and then closed the sidecar

Main-agent rationale:

- historical artifact comparison still looked like the only clean sidecar ownership slice
- even though this round was framed as forward feature delivery rather than simple restoration, the main thread still judged the concrete implementation as locally tractable enough to avoid worker coordination cost
- the added depth changed the code it wrote, but not the delegation topology

### Outcome

- fixed the runtime/control-manifest feature slice in the current workspace:
  - replaced placeholder `quick_reference` values with derived movement/action/dash summary data
  - replaced placeholder `terminal_affordance` values with real server-owned availability and disabled-count data
- fixed the browser replay-overview feature slice in the current workspace:
  - added real visibility/filter-status overview cards
  - replaced placeholder strings with computed summary lines driven by actual filter state
  - added shared entry-visibility helpers so the overview and timeline use the same filtering logic
- produced a sibling-round evidence table showing:
  - the control-manifest overview gap is already visible in rounds 17 through 19
  - the replay-overview surface itself only appears in round 20

Validation:

- `python -m unittest test.test_control_manifest_contract test.test_control_manifest_overview test.test_salvage_run_web -v`
- `node test/test_web_app_replay_filters.js`
- `node test/test_web_replay_shell_markup.js`
- `node test/test_web_replay_inspector_copy.js`
- `node test/test_web_replay_overview_metrics.js`
- `node test/test_web_replay_overview_markup.js`
- reported pass on all six checks

Usage:

- `input_tokens = 848434`
- `cached_input_tokens = 795392`
- `output_tokens = 15317`

## Round 21

### Intent

Run a matched reasoning-effort comparison against the seeded Round 20 workload:

- same current-workspace feature-delivery task shape
- same sibling-round evidence requirement over rounds 17 through 19
- same validation commands
- same model family
- only change `reasoning effort` from `medium` to `high`

The goal was to measure whether a higher reasoning setting would change subagent willingness or the sidecar lifecycle on an otherwise fixed task.

### Workspace

- `E:\agent_misc\.tmp_test\web_port_round21_20260320`

### Outputs

- final message: `E:\agent_misc\.tmp_test\web_port_round21_20260320_last.txt`
- event log: `E:\agent_misc\.tmp_test\web_port_round21_20260320_events.jsonl`

### Model / Runtime

- `model = gpt-5.4`
- `reasoning effort = high`
- `sandbox = workspace-write`
- `approval_policy = never`

### Observed Routing

Completed collaboration calls:

- `spawn_agent = 1`
- no completed `wait` call recorded in the successful event log
- no completed `close_agent` call recorded in the successful event log

Observed delegation pattern:

- one `explorer` sidecar was launched for sibling-round evidence over rounds 17 through 19
- no implementation worker was launched
- no `reviewer` subagent was launched
- the main thread still handled all feature delivery and validation locally
- the final answer still cited sidecar-backed evidence, but the successful event log did not show the explicit `wait`/`close_agent` lifecycle seen in round 20

Main-agent rationale:

- raising reasoning effort changed neither the chosen sidecar role nor the implementation topology
- the main thread still treated history scan as the only clean sidecar slice
- the higher-reasoning run produced a slightly different evidence framing, but not a different delegation strategy

### Outcome

- fixed the same runtime/control-manifest feature slice as round 20:
  - derived real `quick_reference` summary data
  - derived real `terminal_affordance` summary data
- fixed the same browser replay-overview feature slice as round 20:
  - implemented overview cards
  - implemented computed visibility/filter-status summaries
  - reused shared entry-visibility helpers for overview and timeline behavior
- produced a sibling-round evidence table that framed both incomplete surfaces as absent through round 19, yielding a tighter supported introduction window of round 20 or later

Validation:

- `python -m unittest test.test_control_manifest_contract test.test_control_manifest_overview test.test_salvage_run_web -v`
- `node test/test_web_app_replay_filters.js`
- `node test/test_web_replay_shell_markup.js`
- `node test/test_web_replay_inspector_copy.js`
- `node test/test_web_replay_overview_metrics.js`
- `node test/test_web_replay_overview_markup.js`
- reported pass on all six checks

Usage:

- `input_tokens = 761977`
- `cached_input_tokens = 664576`
- `output_tokens = 14755`

## Aggregate Finding

The progression across twenty-one rounds is now clear:

- rounds 1 through 3 stayed entirely local
- round 4 used one worker plus one required reviewer
- round 5 used one worker without a reviewer requirement
- round 6 used two workers without a reviewer requirement
- round 7 returned to fully local execution on a symptom-driven diagnosis round
- round 8 stayed fully local on a broader cross-surface incident round
- round 9 stayed fully local on a two-symptom incident-correlation round
- round 10 finally used an `explorer` sidecar on a regression-origin audit round
- round 11 used an `explorer` sidecar and incorporated its result into a gated evidence table
- round 12 used both an `explorer` sidecar and a voluntary `reviewer`
- round 13 used an `explorer` sidecar again, but dropped `reviewer` once the prompt stopped suggesting that review might be worthwhile
- round 14 used an `explorer` sidecar again, and still did not add `reviewer` even after the current-workspace replay-contract fix became broader and riskier
- round 15 used an `explorer` sidecar again, but still did not add either an implementation worker or a reviewer even after the prompt explicitly highlighted a clean browser-side ownership boundary
- round 16 used an `explorer` sidecar again, but still did not add either an implementation worker or a reviewer even after the browser-side ownership block expanded across template, styles, browser logic, and focused browser tests
- round 17 used an `explorer` sidecar again, but still did not add either an implementation worker or a reviewer even after the prompt split the current round into two disjoint implementation blocks
- round 18 used an `explorer` sidecar again, but still did not add either an implementation worker or a reviewer even after both implementation blocks were made heavier and each gained extra acceptance surfaces
- round 19 used an `explorer` sidecar again on the first cross-feature repair round, but still did not add either an implementation worker or a reviewer, and ultimately fell back to local sibling-round comparison when the sidecar ran late
- round 20 used an `explorer` sidecar again on the first cross-feature forward-feature round, but still did not add either an implementation worker or a reviewer even after the work moved from restoration into genuine feature delivery
- round 21 reran the round 20 workload at higher reasoning effort and still stayed `explorer`-only, with no worker and no reviewer

Most important behavior:

- it routes by the complexity and coupling of the current round, not by the nominal size of the overall workload
- an explicit task list is not enough to trigger delegation if the agent believes the tasks share a schema boundary
- high token consumption alone does not push it toward subagents
- by default it prefers to shrink the round into a locally tractable slice instead of using child agents
- cleaner ownership plus an explicit independent-review requirement can change that behavior
- once ownership becomes cleaner, delegation can continue even without a forced review gate
- when ownership is made explicit enough, the main agent will scale to two implementation workers
- even then, the main thread still keeps integration, docs, parity checks, and final validation local
- a symptom-driven round does not automatically trigger `explorer`; if the symptom is narrow enough to trace quickly, the main agent still prefers local diagnosis
- even when the symptom broadens across backend and frontend replay surfaces, the main agent still prefers local diagnosis if it can compress the work into a single correlated incident pass
- even a two-symptom correlation task is not enough when the search surface remains inside one disposable workspace and one bounded replay feature slice
- historical artifact search across sibling disposable rounds is finally sufficient to trigger `explorer`
- even then, the main thread does not automatically let the sidecar onto the critical path; it will fall back to local comparison if the sidecar is late
- if the prompt makes historical evidence a true completion gate, the main thread will wait and incorporate sidecar output into the final closeout
- explorer becomes materially useful when its ownership is clean, read-only, and separate from the implementation slice
- voluntary reviewer is now reachable, but only after the prompt made the local fix explicitly contract-sensitive and mentioned optional review as worthwhile
- reviewer was used as a final risk screen, not as a required gate that materially changed the implementation
- when the history-audit gate remains but the reviewer hint is removed, `explorer` still appears while `reviewer` disappears
- even after broadening the local replay-contract risk surface across summary, step, parity, and focused JS coverage, reviewer still does not appear without an explicit hint
- even explicitly pointing out a clean worker-friendly browser boundary is not enough to guarantee worker delegation when the main agent still considers the slice locally tractable
- even materially enlarging the browser-side ownership block is not enough to guarantee worker delegation when the main agent still believes the round can be closed locally without coordination cost
- even explicitly splitting the round into Python-side and browser-side implementation blocks is not enough to guarantee worker delegation when the agent believes it can still compress the work into one local pass
- even adding more acceptance weight to both disjoint blocks is not enough to guarantee worker delegation when the underlying task family remains compressible to the main agent
- even moving from replay-only repair slices to a cross-feature repair round is not enough to guarantee worker delegation when the concrete fixes still look like shallow known-good restorations
- even moving from shallow restoration to a deeper cross-feature feature-delivery round is not enough to guarantee worker delegation when the main agent still sees the current slice as locally tractable
- in the first matched `medium` versus `high` comparison on the same feature-delivery round, changing reasoning effort did not change delegation topology

Current qualitative conclusion:

- subagent willingness is low by default
- the routing policy is conservative and coupling-sensitive
- the threshold for delegation is higher than "multi-file web work" or "task list with obvious subtasks"
- clean ownership is now confirmed as the main lever for implementation-worker delegation
- mandatory review was one way to trigger the first delegation event, but it is not necessary once the ownership split is obvious enough
- voluntary independent review has appeared exactly once so far, under explicit optional-review framing
- `explorer` has now appeared, but only on a clean read-only historical audit task
- the `explorer` threshold still appears meaningfully higher than the worker threshold
- current evidence suggests that single-workspace diagnosis is below the `explorer` threshold even when the prompt explicitly invites diagnosis delegation
- current evidence suggests that the main agent treats `explorer` as expendable sidecar support by default, but it will rely on it when the audit output is an explicit completion gate
- current evidence suggests that a prompt-level ownership hint alone is weaker than true perceived implementation pressure for triggering worker delegation
- current evidence suggests that even a larger clean browser-side block is still weaker than true perceived implementation pressure for triggering worker delegation in this workload family
- current evidence suggests that prompt-level decomposition into multiple clean blocks is still weaker than the main agent's own tendency to compress replay-contract work into a single local implementation pass
- current evidence suggests that heavier acceptance weight inside the same replay-contract family still does not materially change that compression behavior
- current evidence suggests that cross-feature decomposition alone is still weaker than perceived implementation depth; shallow repair work across multiple features remains compressible to the main agent
- current evidence suggests that even deeper cross-feature feature delivery is still compressible enough to stay below the no-reviewer-hint worker threshold in this workload family
- reviewer threshold is higher than explorer threshold, but not unreachable
- current evidence now more strongly suggests that voluntary reviewer usage is prompt-sensitive and not yet robustly triggered by broader replay-contract risk in the current workspace alone
- current evidence also suggests we still have not crossed the no-reviewer-hint worker threshold in this replay-contract family, even after making the browser-side implementation slice larger, adding a second disjoint Python-side block, and giving both sides extra acceptance surfaces
- current evidence now also suggests that the first cross-feature repair round still stays below that threshold when each block can be solved as a relatively small local restoration
- current evidence from one matched parameter pair also suggests that moving `gpt-5.4` from `medium` to `high` may change evidence framing and token profile before it changes delegation behavior

## Proposed Next Test

### Name

`web_port_large_task_round_1`

### Goal

Use the routing probe through Round 21 as enough evidence that this workload family is conservative by default.

For the next batch, stop treating subagent willingness as the primary open question.
Instead, run one explicit batch of large web-port delivery tasks and compare end-to-end outcomes.

Record subagent usage, but only as secondary metadata.

### Task Source

Use the concrete task set in:

- `E:\agent_misc\subagent_lab\docs\web-port-large-task-round-20260320.md`

### Batch Shape

- run three standalone `large` tasks instead of another parameter-only rerun
- seed each task from the right web-port milestone baseline instead of the current console-only template
- keep model family, validation discipline, and reporting format matched across modes
- do not vary reasoning effort again until this batch establishes a clearer large-task baseline
- do not add reviewer hints or explicit delegation nudges beyond the generic repo workflow wording

### Tasks

1. `large_web_port_vertical_slice`
- first browser-playable vertical slice with snapshot contract, local server, board/HUD/log rendering, and command submission

2. `large_web_port_replay_parity_workbench`
- deterministic replay loading, step/autoplay controls, browser replay surfaces, and console-versus-web parity checks

3. `large_web_port_operator_polish`
- server-owned help/control metadata, richer inspection and visualization, and concise terminal-summary presentation

### Success Signal

- each task is large enough to produce a meaningful end-to-end comparison on time, tokens, validation, and judged quality
- the batch gives a clearer large-task efficiency baseline than the current console-only `large` bucket
- subagent usage is still recorded, but it no longer determines whether the round was worth running

### Failure Interpretation

If the batch still collapses to mostly local execution, treat that as workload metadata rather than as the next thing to optimize for.

The next move should then be to change baseline maturity or task family, not to spend more rounds on willingness-only probing.
