# Subagent Validation 2026-03-19

Note:

- This document records the earlier validation phase where entry routing was expressed through explicit `monitor` / `default` agents.
- The current workspace has since moved that same routing behavior into the main Codex session to reduce one extra entry hop.

## Goal

Validate that the new native subagent routing setup in this workspace behaves as intended:

- monitor-style routing is the logical entry layer
- routine rounds do not default through `supervisor`
- implementation work routes across `worker_low`, `worker`, and `worker_high`
- `reviewer` remains the default quality gate

## Routing-Only Checks

Three routing-only Codex runs were executed without editing files.

Results:

- low-complexity local help-text plus adjacent test scenario -> `worker_low`
- medium-complexity scan telemetry plus test/doc scenario -> `worker`
- high-complexity shared summary contract across interactive, `--script`, `--quiet-script`, and tests -> `worker_high`

These checks confirmed that the routing rubric was selecting the intended worker tier for representative small, medium, and high-coupling rounds.

## End-to-End Checks

### `worker_low` Round

Validation round:

- narrow help-path copy tweak
- routed through a monitor-style pass
- implemented in the low worker tier
- followed by a reviewer-style pass

Observed result:

- `worker_low` was selected
- reviewer returned `approve`
- `python -m unittest test.test_salvage_run -v` passed with `26` tests

### `worker_high` Round

Validation round:

- shared terminal summary contract across interactive, scripted, and quiet-script flows
- routed through a monitor-style pass
- implemented in the high worker tier
- followed by a reviewer-style pass

Observed result:

- `worker_high` was selected
- reviewer initially returned `request_rework` because win/fail finish-path coverage was incomplete
- the round was reworked with bounded additional tests
- reviewer then returned `approve`
- `python -m unittest test.test_salvage_run -v` passed with `29` tests

This was the stronger validation because it showed `reviewer` acting as an actual stop/go gate instead of a passive final summary.

## Notes

- `supervisor` was intentionally kept out of these default-flow checks.
- The real product code changes made only for validation were cleaned up afterward so the workload stays stable.
- The native collaboration event stream showed the review pass clearly, but it did not expose a perfectly clean “project custom reviewer name” marker in every event. Functionally the flow still matched the repo’s reviewer contract.

## Current Conclusion

The current native setup is working well enough to use on real tasks:

- entry policy routes through monitor-style semantics
- worker tiering is behaving as intended
- `reviewer` can block and approve bounded implementation rounds
- `supervisor` is no longer required for the standard path
