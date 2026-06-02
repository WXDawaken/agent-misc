# Anchor Agent Sample Matrix

## Purpose

Summarize what the current `anchor_agent` workload has already covered, what remains missing, and what the next collaboration step should be.

This doc is intentionally about experiment coverage, not product backlog completeness.

## Current Sample Matrix

| Sample | Kind | Primary Owner | Cross-Boundary? | What It Proves |
| --- | --- | --- | --- | --- |
| `positive_preview_metadata_extension` | Positive | `core` then `plugin` | Yes, but sequential | Additive preview metadata can evolve in the core and be adopted by the plugin without introducing execution behavior. |
| `positive_missing_snapshot_capability` | Positive | `plugin` then `core` | Yes, but sequential | A missing capability can originate in consumer-side snapshot shape and justify a protocol/planner update on the service side. |
| `positive_plugin_selection_lifecycle_probe` | Probe | `plugin` | Yes, mailbox-first but local | A more realistic editor-facing request can still stay local: `plugin_dev` wired the dock to selection-change lifecycle events, reused plugin-local snapshot building, and updated/reset the dock without touching core or protocol files. |
| `godot_headless_editor_plugin_smoke` | Probe | `plugin` | No | A real Godot 4.6.2 headless editor load exposed and then verified the plugin entry path in `plugin.cfg`, raising confidence that the shell can be loaded by Godot rather than only inspected by Python tests. |
| `godot_visible_editor_selection_smoke` | Probe | `plugin` | No | A real Godot 4.6.2 editor window loaded the temporary selection scene, displayed the registered `AgentDock`, and refreshed selected-node target details for `CharacterBody3D` scene nodes. |
| `negative_existing_requires_confirmation_sufficient` | Negative | `plugin` | No | The existing `requires_confirmation` field was already enough for a stable generic confirmation callout, so the plugin should handle that locally instead of escalating schema churn. |
| `negative_schema_churn_without_need` | Negative | `plugin` | Yes, mailbox-first restraint | A mailbox request that explicitly asked for a new `confirmation_banner_label` field still stayed local: `plugin_dev` recognized that `requires_confirmation` already supported the generic dock callout, finished with `changed_files: []`, and never activated `core_dev`. |
| `positive_mailbox_confirmation_details_round` | Positive | `plugin` then `core` then `plugin` | Yes, mailbox-first multi-turn | `plugin_dev` can request one bounded confirmation-detail contract, `core_dev` can add that field without widening execution scope, and `plugin_dev` can later resume from thread state to adopt it after peer completion. |
| `audit_confirmation_details_contract_gap` | Audit | `supervisor`-style review | Yes, mailbox-first follow-up review | The first mailbox-first confirmation-details round stayed bounded, and the audit exposed one real contract gap: `requires_confirmation` did not enforce `confirmation_details`. A follow-up fix now closes that invariant at the model layer and adds a regression test. |
| `negative_wrong_front_door_core_only_copy` | Negative | `core` | Yes, mailbox-first routing | A plugin-local copy request sent to `core_dev` should end in one deferred reply with no core edits, proving the service side can refuse the wrong front door cleanly. |
| `negative_plugin_copy_only` | Negative | `plugin` | No | Pure dock wording and empty-state improvements should stay local to the plugin. |
| `negative_core_wording_only` | Negative | `core` | No | Pure suggestion/explanation wording changes should stay local to the core. |
| `negative_boundary_break_execute` | Negative | `core` runtime guard | Yes | The core/plugin execution split is now enforced at runtime instead of only by doc convention. |
| `negative_ambiguous_execute_vs_preview` | Negative | `core` runtime guard | Yes | Ambiguous preview-versus-execute intent now yields explicit clarification instead of implicit guessing. |

## Coverage By Dimension

### Covered Well

- Additive protocol evolution without execution creep
- Consumer-side capability discovery feeding service-side planner behavior
- Local-only plugin tasks
- Local-only core tasks
- Restraint when an existing field is already sufficient
- Restraint against unnecessary schema churn even after one successful mailbox-first contract addition
- Execution boundary enforcement
- Clarification-required behavior for ambiguous intent
- A full mailbox-first `plugin -> core -> plugin` round including watcher restart and thread-registry-backed continuation
- Wrong-front-door refusal on a real mailbox thread

### Covered Partially

- Protocol negotiation
  - We now have one bounded mailbox-first contract request, but not a disagreement or arbitration loop yet.
- Fixture-driven development
  - The fixture base is healthy and now exercised in one real role-separated round, but only on a single preview-contract seam so far.
- Real Godot/editor behavior
  - We now have one repo-inspectable selection lifecycle seam, one headless editor-load smoke, and one visible dock/selection manual smoke; full plan-preview capability differences still need a live-editor pass.

### Not Covered Yet

- Any durable task-state or handoff behavior specific to `anchor_agent`

## What This Means

The environment is past the "does it exist?" stage.

It now has enough structure to stop accumulating one-off local samples and start measuring real coordination value.

Continuing to add more single-process samples would still produce information, but at a lower rate than the next more realistic step.

## Recommendation

Do not add another same-shape local sample immediately.

The next batch should build on the first mailbox-first `anchor_agent` batch rather than returning to more local-only samples:

- `plugin_dev`
- `core_dev`
- optional `reviewer` later, but not in the first round

## Recommended Next Batch

### 1. Visible Live Godot Smoke Or Durable Lifecycle Probe Follow-Up

Shape:

- Run either:
  - a thin visible editor selection-change smoke on top of the new plugin lifecycle seam
  - or a more explicit durable task-state probe on top of the existing mailbox-first scaffold

Expected:

- expose whether the current fixture-first success still holds when one more real environment or lifecycle variable is added

Why first:

- The environment now has enough positive and negative routing evidence that the next highest-value gap is no longer basic plugin wiring, but either a live editor context or richer lifecycle durability.

## Repo Recommendation

Do not split `anchor_agent` into its own repo yet.

Current recommendation:

- keep it inside `subagent_lab`
- complete one mailbox-first batch
- then decide whether the environment is stable and distinct enough to justify a dedicated repo

The reason is simple: right now the main unknown is collaboration shape, not repo hygiene.

## Exit Criteria For The Next Decision

Re-evaluate after the next review/routing batch when we can answer:

1. Does the environment still produce useful signal once real role separation is introduced?
2. Do the `plugin_dev` and `core_dev` boundaries stay clean under multi-turn work?
3. Does mailbox-first coordination reveal new failure modes that the current fixture-first local samples could not expose?
4. Is the environment now distinct enough from `Salvage Run` to justify separate benchmark treatment?
