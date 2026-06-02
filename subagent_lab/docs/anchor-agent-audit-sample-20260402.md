# Anchor Agent Audit Sample 2026-04-02

## Sample

- `audit_confirmation_details_contract_gap`

## Scope

- Audit the first mailbox-first positive `anchor_agent` round:
  - `positive_mailbox_confirmation_details_round`
- Check whether the new `confirmation_details` contract stayed bounded and whether the protocol guarantee is actually enforced in code.

## Finding

### `confirmation_details` is documented as required but not enforced

The protocol document says `ActionPlan.confirmation_details` is required when `requires_confirmation` is `true`.

Current code does not enforce that invariant at the model or API boundary:

- `anchor_agent_core/ir/action_plan.py` allows `confirmation_details = None` even when `requires_confirmation` is true.
- `anchor_agent_godot_plugin/addons/anchor_agent/ui/agent_dock.gd` silently falls back to generic confirmation copy when the field is missing.

This means a future planner change can accidentally ship a confirmation-required plan without `confirmation_details`, and the plugin would mask that contract drift instead of surfacing it.

## Why This Matters

- The first mailbox-first contract round was meant to prove that one bounded new field improved plugin rendering.
- Without enforcement, the protocol guarantee is only a doc promise.
- The plugin fallback is still useful for resilience, but it currently also hides server-side regressions from fixture and mailbox-first review loops.

## What Stayed Clean

- The field addition itself remained bounded to preview/confirmation semantics.
- Core did not cross the execution boundary.
- Plugin and core file ownership remained clean in the original mailbox-first round.
- The finding is about contract enforcement, not about boundary breakage or over-broad schema growth.

## Residual Risk

- Future confirmation-required actions could omit `confirmation_details` without failing tests if the plugin continues to render the generic fallback.
- Reviewers may incorrectly conclude the richer confirmation contract is still present because the dock would continue to show a usable confirmation callout.

## Recommended Follow-Up

1. Add an `ActionPlan` invariant so `requires_confirmation == true` requires `confirmation_details`.
2. Keep the plugin fallback for defensive rendering, but make it easier to detect missing structured data in tests or logs.
3. Add one regression test that intentionally constructs a confirmation-required plan without `confirmation_details` and expects validation failure.

## Follow-Up Status

Follow-up 1 and 3 have now landed in the next local fix:

- `ActionPlan` now enforces the `requires_confirmation -> confirmation_details` invariant.
- The test suite now includes a regression that expects validation failure when confirmation details are omitted from a confirmation-required plan.
