# Mail4Agent Bridge Pattern Memo

## Question

Why does the same pattern keep appearing on bridge-like large integration tasks?

- objective results are often mixed, noisy, or sensitive to replicate order
- blinded judged-quality results keep leaning toward `subagents`

This memo summarizes the current working explanation from the completed Python and Rust bridge-delivery benchmark lines.

## Repeated Pattern

### Python bridge task

Source line:

- `E:\agent_misc\docs\mail4agent-feature-round3-eval-20260323.md`

Observed outcome:

- objective on `large_mail4agent_webhook_or_stdio_bridge_delivery` favored `single_xhigh` on both replicates
- judged on the same task favored `subagents` on both blinded passes

### Rust bridge task

Source line:

- `E:\agent_misc\docs\mail4agent-rust-feature-benchmark-round2-20260323.md`

Observed outcome:

- `r1` objective favored `subagents`
- reversed-order `r2` objective favored `single_xhigh`
- judged favored `subagents` on both blinded passes

So the repeated pattern is not simply "subagents always win bridge tasks."

It is more specific:

- bridge-like tasks often produce unstable or replicate-sensitive objective winners
- but judged quality more consistently leans toward `subagents`

## Most Likely Causes

### 1. Objective validation is narrower than the real quality surface

The bridge tasks usually validate a small number of happy-path and retry-path checks.

That means objective success mostly measures:

- whether the missing route or helper exists
- whether the acceptance test passes

It does not fully capture:

- robustness around heartbeat / retry edge cases
- how tightly the implementation reuses existing shared paths
- whether the extra surface area stayed narrow
- whether the public evidence is clean and confidence-inspiring

Those are exactly the dimensions the judged rubric sees through:

- `scope_control`
- `code_quality`
- `evidence_quality`

### 2. `subagents` often spends extra work on task-aligned robustness

Across the judged bridge packets, the preferred candidate was repeatedly the one that used its extra budget on changes more directly tied to the bridge contract.

Examples:

- Python bridge judged favored the candidate that looked more production-robust, even when objective time and token use favored `single_xhigh`
- Rust bridge `r1` judged favored the candidate that stayed narrower and also removed pipe-warning noise from the evidence
- Rust bridge `r2` judged favored the candidate that spent the extra change on explicit heartbeat-path exercise during `bridge-once`

So the repeated judged preference is not arbitrary. It is repeatedly rewarding "better task-aligned extra margin."

### 3. `subagents` can reduce attention diffusion on bridge tasks

The bridge runs suggest a second mechanism besides simple parallelism:

- the child agents are usually not full code-writing workers
- they are mostly bounded readers that answer side questions about contracts, harness behavior, or the current route surface
- the parent then absorbs those compressed answers and continues implementation locally

That matters because bridge tasks force the agent to juggle several side concerns at once:

- the actual missing route or helper
- heartbeat and retry semantics
- machine-readable CLI output shape
- test-harness quirks
- docs or progress updates

When those all stay in one serial working set, a strong single agent can drift into over-reasoning:

- exploring too many implementation branches
- mixing task-aligned changes with broader cleanup
- spending extra budget on low-priority polish before the acceptance boundary is fully pinned down

The `subagents` topology partially externalizes those side questions.

Instead of the parent carrying all of them in one stream, the parent gets:

- one bounded report on the implementation boundary
- one bounded report on the acceptance or operator contract
- sometimes one small delegated edit on a very narrow file

That does not eliminate rework, but it appears to reduce the chance that the parent diffuses attention across too many concerns before the minimal shape is clear.

This interpretation fits the observed bridge solve paths:

- Python bridge runs used two advisory helpers, one implementation-facing and one docs or harness-facing
- Rust bridge `r1` used two advisory helpers, one for the Python semantic oracle and one for the Rust route baseline
- Rust bridge `r2` kept those two advisory helpers and added one short-lived test-only worker

So a plausible explanation is not just "subagents parallelize better."

It is also:

- on hidden-contract integration tasks, `subagents` can reduce attention spread and scope drift by turning side questions into bounded sidecars

### 4. `single_xhigh` has a stronger serial-closure tendency

On these bridge tasks, `single_xhigh` often uses its extra serial budget on things like:

- README additions
- broader regression passes
- extra cleanup
- more expansive final delivery framing

Those actions are often reasonable engineering moves, but they can cut both ways:

- sometimes they help
- sometimes they look like scope expansion relative to the task packet

In judged review, that can reduce `scope_control` even when correctness remains perfect.

### 5. Bridge tasks are unusually sensitive to execution-path noise

These tasks combine multiple moving parts:

- HTTP route surface
- backend helper or storage semantics
- heartbeat / lease timing
- retry behavior
- subprocess-based test harness behavior

That makes objective runtime and token results more sensitive to:

- which detour the agent hits first
- whether extra validation is run
- local execution noise
- mode-order or warm-start effects

This helps explain why the Rust bridge objective winner flipped between `r1` and reversed-order `r2`, while judged preference did not.

### 6. The judged rubric structurally amplifies this task shape

For bridge and integration tasks, the four judged dimensions are not equally likely to move.

Correctness often ties at `5`.

The real separation usually happens in:

- `scope_control`
- `code_quality`
- `evidence_quality`

That creates a recurring pattern where:

- both candidates pass the same tests
- the judged winner is decided by quality margin rather than hard correctness

## What This Does Not Mean

It does not mean:

- `subagents` is globally better on Rust feature-port work
- `subagents` is always faster on bridge tasks
- objective metrics are unimportant

The current completed evidence still shows:

- small Rust feature-port tasks favor `single_xhigh`
- medium Rust feature-port tasks favor `single_xhigh`
- bridge-like large tasks are where the split appears

## Current Working Read

The best current interpretation is:

- small or medium bounded feature-port tasks are still better default territory for `single_xhigh`
- large bridge or integration tasks expose more hidden quality surface than objective validation alone captures
- on those tasks, judged quality currently leans more reliably toward `subagents`, even when objective speed or token results are mixed

In short:

- objective on bridge tasks measures "who passed most cheaply this time"
- judged on bridge tasks is closer to "which implementation leaves better quality margin"

## Policy Implication

For now, the safest working policy is task-shape based:

- use `single_xhigh` as the default for tighter bounded Rust feature-port work
- treat bridge-like large integration tasks as special cases
- on those special cases, do not rely on a single objective replicate alone
- when quality matters, give extra weight to the judged signal, which currently leans `subagents`

## Status

This is still a working explanation, not a final gold-standard conclusion.

Reasons:

- judged passes are still single-rater Codex judgments
- bridge tasks still have only a small number of replicates
- objective outcomes on large bridge tasks remain somewhat replicate-sensitive

But the pattern is now repeated enough across both Python and Rust bridge lines that it is useful as an operational interpretation.

## Follow-up Test Direction

The next useful tests should not simply be "more bridge replicates."

They should separate three possibilities:

- the effect is specific to bridge or subprocess-integration tasks
- the effect is broader to large hidden-quality tasks
- the effect is mostly noise from a small number of replicates

For the current recommended follow-up slate, see:

- `E:\agent_misc\docs\mail4agent-rust-feature-followup-tests-20260324.md`
