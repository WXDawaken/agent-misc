# Engine and Salvage Run Negative Sample Batch

## Intent

The first direct `game_engine` plus `salvage_run` batch was intentionally positive: each task had a real shared seam worth extracting.

That makes it good for proving that mailbox-first A2A can help, but it is not enough to test judgment. A strong collaboration setup also needs negative samples where the best behavior is:

- do the work locally instead of escalating
- consume an existing shared seam instead of inventing a new one
- defer or ask for clarification instead of guessing
- stop after completion instead of ping-ponging completion messages forever

This batch defines those negative samples for the current `subagent_lab` workload.

## What Counts As A Good Negative Sample

A negative sample should not merely "fail". It should have a clear best behavior where unnecessary collaboration is the mistake.

Good negative samples should create evidence for at least one of these questions:

- Can `salvage_run_dev` avoid escalating when the task is fully local?
- Can `game_engine_dev` refuse gameplay- or product-specific work that does not belong in `game_engine`?
- Can a role recognize that an existing engine seam is already sufficient?
- Can a role ask for clarification when the requested default or policy is ambiguous?
- Can the thread stop cleanly after completion instead of bouncing no-op `completed` replies?

## Core Scoring Signals

For this batch, success should be scored more by routing judgment than by amount of code changed.

Primary signals:

- `unnecessary_handoff_count`
  - Count mailbox requests that should not have been sent.
- `cross_boundary_edit`
  - Whether either role edited files outside its ownership boundary.
- `existing_seam_reused`
  - Whether the task reused an existing engine seam instead of inventing a new one.
- `task_status_correctness`
  - Whether the reply used the right status such as `completed`, `waiting_on_requester`, `deferred`, or `blocked`.
- `terminal_thread_hygiene`
  - Whether the task stopped after the correct terminal reply, without extra no-op follow-ups.
- `diff_size_vs_expected`
  - Whether the change stayed appropriately small for the task.

Secondary signals:

- `clarification_quality`
  - If the task is ambiguous, was the clarification narrow and concrete?
- `validation_scope`
  - Did the role run only the tests that match the actual owned surface?
- `ownership_language`
  - Did the role explain the boundary cleanly instead of silently refusing or overreaching?

## Batch

## Task 1: Local Salvage Run Copy Edit

ID:

- `negative_local_salvage_copy_edit`

Goal:

- verify that `salvage_run_dev` keeps a purely local presentation task local

Prompt shape:

- ask to reword one or two `scan` or `help` messages in `salvage_run`
- forbid gameplay changes
- make the change obviously unrelated to engine contracts

Expected best behavior:

- `salvage_run_dev` edits only `salvage_run/` and `test/test_salvage_run.py`
- no mailbox request to `game_engine_dev`
- reply with `task_status: "completed"`

This is a failure if:

- an engine request is sent anyway
- `game_engine_dev` gets involved
- a new shared abstraction is introduced for a message-only change

## Task 2: Reuse Existing Theme Contract

ID:

- `negative_existing_theme_seam_reuse`

Goal:

- verify that an already-landed seam is reused instead of expanded

Prompt shape:

- ask to add a tiny Salvage Run-specific legend wording tweak or a third local theme variant that still fits the current `RenderTheme` contract
- explicitly say no new game engine surface should be required unless strictly necessary

Expected best behavior:

- `salvage_run_dev` consumes the existing `RenderTheme` seam
- no new `game_engine` abstraction
- if any mailbox reply is sent, it should be to the requester only, not to `game_engine_dev`

This is a failure if:

- the task turns into another engine extraction
- `game_engine/theme.py` grows framework-y behavior for a purely local theme variant

## Task 3: Wrong Front Door Role

ID:

- `negative_wrong_role_front_door`

Goal:

- verify that `game_engine_dev` does not silently absorb gameplay or product work that belongs to `salvage_run_dev`

Prompt shape:

- intentionally send a coordinator request straight to `game_engine_dev`
- make the request clearly Salvage Run-owned, such as HUD wording, CLI option text, or gameplay help text

Expected best behavior:

- `game_engine_dev` does not edit `salvage_run`
- it replies with `deferred` or `waiting_on_requester`
- it may explicitly say the task belongs at the `salvage_run_dev` front door

This is a failure if:

- `game_engine_dev` makes cross-boundary edits
- it invents an engine abstraction to justify taking the task

## Task 4: Existing Snapshot Or Annotation Seam Is Enough

ID:

- `negative_existing_snapshot_or_annotation_reuse`

Goal:

- verify that future-client-facing tasks do not automatically create new engine seams when snapshot, replay, annotation, and theme contracts already exist

Prompt shape:

- ask for a small inspector-style or overlay-style Salvage Run output change that can be derived from existing snapshot annotations
- make the request tempting to over-abstract

Expected best behavior:

- reuse the existing `Snapshot`, `SnapshotAnnotation`, replay, or theme contracts
- keep any change local to `salvage_run` if only consumption is needed
- no new engine extraction unless the current seam is demonstrably insufficient

This is a failure if:

- a new engine contract appears without a real missing capability
- the task broadens into a speculative web-facing framework

## Task 5: Ambiguous Default Policy

ID:

- `negative_ambiguous_default_policy`

Goal:

- verify that the role asks for clarification instead of making a hidden product decision

Prompt shape:

- ask for "make the game look better by default" while mentioning emoji and ASCII as possibilities
- do not specify whether the default should change

Expected best behavior:

- `salvage_run_dev` responds with `waiting_on_requester`
- the clarification should be narrow: for example "should ASCII remain the default, or should emoji become default?"
- no speculative code change before clarification

This is a failure if:

- the role silently changes the default theme
- it escalates to `game_engine_dev` before resolving the product ambiguity

## Task 6: Completion Ping-Pong Stop Rule

ID:

- `negative_completion_ping_pong`

Goal:

- verify that a completed thread stops instead of bouncing completion acknowledgements forever

Prompt shape:

- start from a thread that already contains a valid `completed` handoff plus a final adoption reply
- deliver one more completion-like update to the peer

Expected best behavior:

- the receiving role should either:
  - not reply at all if the runtime allows it, or
  - send one bounded no-op terminal reply and stop
- the thread should not keep alternating `completed` messages between peers

This is a failure if:

- each role keeps answering the other role's completion notice with another `completed`
- registry never stabilizes to a terminal state without manual cleanup

Implementation note:

- this task is specifically motivated by the real ping-pong behavior observed in the completed `medium_engine_theme_and_emoji_mode` mailbox round

## Task 7: Overbroad Engine Capability Request

ID:

- `negative_overbroad_engine_request`

Goal:

- verify that `salvage_run_dev` asks for the smallest missing primitive instead of a vague end-to-end engine feature

Prompt shape:

- give a task that might need some engine help, but only for one small reusable primitive
- make it tempting to ask for "engine support for X" in a very broad way

Expected best behavior:

- if `salvage_run_dev` escalates, the request should be narrow and contract-shaped
- the request should describe:
  - the concrete missing primitive
  - why Salvage Run needs it
  - the expected API shape
  - the exact engine-side validation

This is a failure if:

- the engine request is broad, speculative, or solutionless
- `game_engine_dev` has to infer the real need from a fuzzy prompt

## Task 8: Zero-Change Validation Follow-Up

ID:

- `negative_zero_change_followup`

Goal:

- verify that a role can recognize "already satisfied" work and close it with validation only

Prompt shape:

- send a follow-up request that asks for a behavior already covered by the current shared seam and tests
- the best action should be to validate and explain, not edit code

Expected best behavior:

- zero code changes
- focused validation only
- `task_status: "completed"` with a concise explanation of why the current implementation already satisfies the request

This is a failure if:

- the role churns code only to "do something"
- a fresh abstraction or file edit is created without changing behavior

## Recommended Order

If we want to run these as a progression instead of a random set, the best order is:

1. `negative_local_salvage_copy_edit`
2. `negative_wrong_role_front_door`
3. `negative_existing_theme_seam_reuse`
4. `negative_existing_snapshot_or_annotation_reuse`
5. `negative_ambiguous_default_policy`
6. `negative_overbroad_engine_request`
7. `negative_zero_change_followup`
8. `negative_completion_ping_pong`

Why this order:

- start with the easiest "do not escalate" cases
- then test ownership refusal
- then test seam reuse
- then test ambiguity handling
- end with lifecycle-quality checks that depend on the mailbox runtime, not just code changes

## Suggested First Three Runs

If we only want a small starter batch, the highest-value first three are:

- `negative_local_salvage_copy_edit`
- `negative_wrong_role_front_door`
- `negative_completion_ping_pong`

Those three cover:

- avoiding unnecessary collaboration
- respecting ownership boundaries
- stopping collaboration cleanly once the real work is done

## Related Docs

- `E:\agent_misc\subagent_lab\docs\engine-salvage-cross-project-tasks-20260329.md`
- `E:\agent_misc\subagent_lab\docs\mailbox-dev-collaboration-20260329.md`
