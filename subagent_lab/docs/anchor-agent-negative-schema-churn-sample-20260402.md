# Anchor Agent Negative Sample 2026-04-02

## Sample

- `negative_schema_churn_without_need`

## Intent

Probe whether the first successful mailbox-first protocol round accidentally trained the workflow to treat every dock tweak as a schema request.

## Scenario

- Send an editor-facing request to `plugin_dev`.
- The request explicitly asks for a new core field:
  - `ActionPlan.confirmation_banner_label`
- The desired behavior is only a generic confirmation header for confirmation-required plans.

## Expected Behavior

- `plugin_dev` should recognize that the current contract is already sufficient.
- The request should not escalate to `core_dev`.
- The thread should finish with either:
  - a local plugin-only handling result, or
  - a zero-change completion that explains why the new field is unnecessary.

## Observed Outcome

- Thread: `aa905dce-a255-4746-8454-68a9cf3d6a93`
- Request message: `d06d1801-2025-4f56-8d68-afb57d996219`
- Reply message: `58a06394-01bd-4639-9533-f3c6d288e938`

`plugin_dev` replied:

- `task_status: "completed"`
- `changed_files: []`
- no mailbox request to `core_dev`

Reply summary:

- the existing plugin dock already renders a generic `Confirmation Required:` header from `ActionPlan.requires_confirmation`
- `confirmation_details` remains optional enrichment, not a prerequisite for the generic callout
- adding `confirmation_banner_label` would be unnecessary schema churn

## Validation

- `python -m unittest anchor_agent.test.test_phase0_assets.AnchorAgentPhase0Tests.test_plugin_dock_mentions_preview_sections -v`

## Additional Evidence

- `core_dev` on-call summary ended with `processed = 0`
- the mailbox thread contains only:
  - coordinator request
  - `plugin_dev` completion reply

## Conclusion

This negative sample behaved as intended.

The mailbox-first success path did not automatically widen into a second, unnecessary protocol round. `plugin_dev` kept the request local, recognized that the existing contract was already enough, and prevented schema churn before it reached `core_dev`.
