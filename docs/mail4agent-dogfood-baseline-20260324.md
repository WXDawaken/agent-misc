# Mail4Agent Dogfood Baseline

## Decision

Use the canonical Python repo checkout as the dogfood baseline root:

- repo: `E:\agent_misc\mail4agent`
- branch base: `main`
- current known commit: `a8b190c1b9c3d5b22d5a0d3a36ce57df40992335`

Do **not** use a benchmark seed or a single benchmark result workspace as the long-lived dogfood baseline.

## Why This Version

### Why `E:\agent_misc\mail4agent` Wins

- It is the only normal git-backed product workspace.
- It already carries the current Python product truth for core mailbox semantics, admin flows, CLI, and UI.
- It is the right place to evolve into a reusable local service for other agents.

### Why Not Use A Benchmark Seed

Do not use:

- `E:\agent_misc\.tmp_test\mail4agent_feature_round4_20260323`

as the long-lived baseline.

Reason:

- it is a benchmark template, not a product home
- it contains benchmark-only runtime hardening and test scaffolding
- it does not represent one integrated, product-ready feature set

### Why Not Use A Single Benchmark Result Workspace

Do not use a per-run workspace such as:

- `E:\agent_misc\benchmarks\results\...\__workspace`

as the baseline.

Reason:

- each one is task-local and only integrates one feature slice
- they carry benchmark-specific progress files, README churn, and validation-specific edits
- no single result workspace currently represents the best integrated all-feature baseline

## Working Recommendation

Build the dogfood baseline as:

1. canonical repo root: `E:\agent_misc\mail4agent`
2. plus selectively promoted Python feature implementations from benchmark-winning workspaces
3. without pulling Rust in as the baseline server yet

This keeps the dogfood stack aligned with the current `Python-first, Rust-selective` decision.

## Wave 1 Features

These are the first features worth promoting into the dogfood baseline.

They are either:

- directly useful for agent-to-agent mailbox use
- supported by stronger benchmark evidence
- or both

### Admin Mailbox Access

Recommended source:

- `E:\agent_misc\benchmarks\results\20260324T_mail4agent_admin_mailbox_access_r2\20260324T080228Z\medium_mail4agent_admin_mailbox_access__single_xhigh__r2__workspace`

Reason:

- explicit-config run
- reversed-order replicate
- objective and judged both acceptable, with `single_xhigh` winning the `r2` judged pass
- directly useful for operator and cross-harness dogfood control

### Retry Queue Visibility

Recommended source:

- `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z\small_mail4agent_retry_queue_visibility__single_xhigh__r1__workspace`

Reason:

- pinned-harness round
- directly useful for real operator visibility during dogfood
- fits the current `single_xhigh`-leaning bounded Python control pattern

### Thread Summary And Unread State

Recommended source:

- `E:\agent_misc\benchmarks\results\20260323T_mail4agent_feature_round3\20260323T035715Z\medium_mail4agent_thread_summary_and_unread_state__single_xhigh__r1__workspace`

Reason:

- pinned-harness round
- high user value for real agent inbox triage
- belongs to the cleaner Python product-surface line, not the bridge-special-case line

## Wave 2 Features

These are good follow-on candidates, but not the first dogfood merge wave.

### Inbox List And Filters

Candidate source:

- `E:\agent_misc\benchmarks\results\20260322T082714Z\small_mail4agent_inbox_list_and_filters__single_xhigh__r1__workspace`

Use later because:

- evidence is good
- but it comes from the older pre-pin batch

### Routing Explain Surface

Candidate source:

- `E:\agent_misc\benchmarks\results\20260322T082714Z\medium_mail4agent_routing_explain_surface__single_xhigh__r1__workspace`

Use later because:

- very useful for operator debugging
- but the Python evidence on this task had a judged exception and came from the older pre-pin batch

### Delivery Audit Timeline

Candidate source:

- `E:\agent_misc\benchmarks\results\20260322T082714Z\large_mail4agent_delivery_audit_timeline__single_xhigh__r1__workspace`

Use later because:

- valuable for observability
- but it is more operator-heavy than mailbox-core dogfood needs
- and it also comes from the older pre-pin batch

### Export Or Import Environment Bundle

Candidate source:

- `E:\agent_misc\benchmarks\results\20260323T_large_config_sanity\20260322T182520Z\large_mail4agent_export_import_environment_bundle__single_xhigh__r1__workspace`

Use later because:

- useful for reproducible environments
- but not required for the first multi-agent communication baseline

## Hold Out For Now

### Webhook Or Stdio Bridge Delivery

Do not make this part of the first dogfood baseline.

Reason:

- it repeatedly showed `objective` and `judged` tension
- it is more integration-heavy than mailbox-core dogfood needs
- it is better treated as a dedicated second-phase integration capability

### Rust Server As Primary Runtime

Do not make Rust the first dogfood baseline runtime.

Reason:

- the split decision is still `Python-first, Rust-selective`
- Rust feature-port work is promising, but still task-shape dependent
- several Rust tasks still rely on Python as the semantic oracle

## Practical Baseline

If we want the fastest path to real dogfood:

- baseline root: `E:\agent_misc\mail4agent`
- language: Python
- first promoted feature wave:
  - admin mailbox access
  - retry queue visibility
  - thread summary and unread state

That gives us:

- better operator control
- better agent inbox triage
- better retry observability

without forcing us to solve the bridge/integration and Rust-promotion questions first.

## Next Step

Create a dedicated dogfood integration workspace or branch from:

- `E:\agent_misc\mail4agent`

Then port the Wave 1 Python features into it before writing the first real multi-agent smoke scenario.
