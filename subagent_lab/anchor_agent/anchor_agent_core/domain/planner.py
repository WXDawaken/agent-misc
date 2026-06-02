"""Rule-based planner for the initial Anchor Agent workload."""

from __future__ import annotations

from ..ir.action_plan import ActionPlan, ConfirmationDetails, PreviewSection
from ..ir.patch_proposal import PatchProposal
from ..ir.object_snapshot import ObjectSnapshot
from ..ir.suggested_action import SuggestedAction


class RuleBasedPlanner:
    def suggest(self, snapshot: ObjectSnapshot) -> list[SuggestedAction]:
        actions: list[SuggestedAction] = []
        if snapshot.type_name == "CharacterBody3D":
            actions.append(
                SuggestedAction(
                    id="validate_movement_setup",
                    title="Validate movement setup",
                    intent="validate_movement",
                    target_ids=[snapshot.object_id],
                    confidence=0.91,
                    risk="low",
                    requires_confirmation=False,
                    rationale=(
                        "Start by checking the movement-facing setup before layering "
                        "on additional character behavior."
                    ),
                    preconditions=["Node type is CharacterBody3D"],
                    tags=["movement", "validation", "character"],
                )
            )
            if not self._has_collision_shape(snapshot):
                actions.append(
                    SuggestedAction(
                        id="review_collision_shape_setup",
                        title="Review collision shape setup",
                        intent="review_collision_shape",
                        target_ids=[snapshot.object_id],
                        confidence=0.89,
                        risk="low",
                        requires_confirmation=False,
                        rationale=(
                            "The selected CharacterBody3D does not advertise a collision "
                            "shape capability, so physics behavior may be incomplete or misleading."
                        ),
                        preconditions=[
                            "Node type is CharacterBody3D",
                            "Collision shape capability is missing",
                        ],
                        tags=["movement", "physics", "collision"],
                    )
                )
            if self._has_script(snapshot):
                actions.append(
                    SuggestedAction(
                        id="add_double_jump_scaffold",
                        title="Add double-jump scaffold",
                        intent="add_double_jump",
                        target_ids=[snapshot.object_id],
                        confidence=0.78,
                        risk="medium",
                        requires_confirmation=True,
                        rationale=(
                            "The node is a CharacterBody3D with an attached script, "
                            "so a script-scaffolded double-jump suggestion is available."
                        ),
                        preconditions=[
                            "Node type is CharacterBody3D",
                            "Attached script is present",
                        ],
                        tags=["movement", "script", "scaffold"],
                    )
                )
        return actions

    def explain(self, snapshot: ObjectSnapshot, action_id: str | None) -> dict[str, object] | None:
        if action_id == "validate_movement_setup" and snapshot.type_name == "CharacterBody3D":
            return {
                "action_id": "validate_movement_setup",
                "title": "Validate movement setup",
                "why": (
                    "Suggested because the selected node is a CharacterBody3D and its "
                    "movement-related configuration should be checked before further edits."
                ),
                "observed_features": [
                    "type_name=CharacterBody3D",
                    "capability=move",
                    f"path={snapshot.path}",
                ],
            }
        if action_id == "review_collision_shape_setup" and snapshot.type_name == "CharacterBody3D" and not self._has_collision_shape(snapshot):
            return {
                "action_id": "review_collision_shape_setup",
                "title": "Review collision shape setup",
                "why": (
                    "Suggested because the selected CharacterBody3D does not advertise "
                    "a collision-shape capability, which makes movement and contact previews incomplete."
                ),
                "observed_features": [
                    "type_name=CharacterBody3D",
                    "capability=move",
                    "capability_missing=has_collision_shape",
                    f"path={snapshot.path}",
                ],
            }
        if action_id == "add_double_jump_scaffold" and snapshot.type_name == "CharacterBody3D" and self._has_script(snapshot):
            return {
                "action_id": "add_double_jump_scaffold",
                "title": "Add double-jump scaffold",
                "why": (
                    "Suggested because the selected node is already a scripted "
                    "CharacterBody3D, so the jump extension can be reviewed in one local scaffold."
                ),
                "observed_features": [
                    "type_name=CharacterBody3D",
                    "capability=move",
                    "capability=has_script",
                    f"property.attached_script_path={snapshot.properties.get('attached_script_path')}",
                ],
            }
        return None

    def plan(self, snapshot: ObjectSnapshot, action_id: str | None) -> ActionPlan | None:
        if action_id == "validate_movement_setup" and snapshot.type_name == "CharacterBody3D":
            return ActionPlan(
                action_id="validate_movement_setup",
                summary="Review the selected character's movement-facing properties and script hooks.",
                risk="low",
                requires_confirmation=False,
                steps=[
                    "Check whether the node exposes movement-related capabilities.",
                    "Inspect key movement properties such as floor snap and gravity scale.",
                    "Highlight any missing script hook or unexpected property combination.",
                ],
                affected_objects=[snapshot.object_id],
                affected_files=[],
                preview_changes=[
                    "No direct file patch is required for the validation preview.",
                    "Preview returns a checklist-oriented assessment only.",
                ],
                preview_sections=[
                    PreviewSection(
                        id="inspection_scope",
                        title="Inspection Scope",
                        lines=[
                            snapshot.path,
                            "Movement-related properties",
                            "Script hook availability",
                        ],
                    ),
                    PreviewSection(
                        id="preview_outcome",
                        title="Preview Outcome",
                        lines=[
                            "No file patch is proposed.",
                            "The plugin should present this plan as a checklist preview.",
                        ],
                        style="note",
                    ),
                ],
                engine_mutations=["none: preview-only validation"],
                rollback_strategy="No rollback required because the validation plan does not apply changes.",
            )
        if action_id == "review_collision_shape_setup" and snapshot.type_name == "CharacterBody3D" and not self._has_collision_shape(snapshot):
            return ActionPlan(
                action_id="review_collision_shape_setup",
                summary="Inspect the selected character for a missing CollisionShape3D or equivalent physics child.",
                risk="low",
                requires_confirmation=False,
                steps=[
                    "Check the selected CharacterBody3D for a CollisionShape3D or CollisionPolygon3D child.",
                    "Confirm that the missing collision capability is intentional rather than an editor setup gap.",
                    "If missing by mistake, prepare a plugin-side reminder before any movement scaffolding is applied.",
                ],
                affected_objects=[snapshot.object_id],
                affected_files=[],
                preview_changes=[
                    "No automatic patch is proposed.",
                    "Preview highlights the missing collision capability and keeps the fix local to the editor.",
                ],
                preview_sections=[
                    PreviewSection(
                        id="missing_capability",
                        title="Missing Capability",
                        lines=["has_collision_shape"],
                        style="note",
                    ),
                    PreviewSection(
                        id="inspection_targets",
                        title="Inspection Targets",
                        lines=[
                            snapshot.path,
                            "CollisionShape3D child",
                            "CollisionPolygon3D child",
                        ],
                    ),
                ],
                engine_mutations=["none: inspection preview only"],
                rollback_strategy="No rollback required because this preview does not apply changes.",
            )
        if action_id == "add_double_jump_scaffold" and snapshot.type_name == "CharacterBody3D" and self._has_script(snapshot):
            return ActionPlan(
                action_id="add_double_jump_scaffold",
                summary="Prepare a safe double-jump scaffold preview for the selected character script.",
                risk="medium",
                requires_confirmation=True,
                steps=[
                    "Locate the attached script referenced by the selected node.",
                    "Preview new jump-count state and a guarded second-jump branch.",
                    "Leave TODO markers so the plugin can present the scaffold as a reviewable local patch.",
                ],
                affected_objects=[snapshot.object_id],
                affected_files=[str(snapshot.properties.get("attached_script_path"))],
                preview_changes=[
                    "Add placeholder jump counter state.",
                    "Insert a second-jump branch guarded by TODO comments.",
                ],
                preview_sections=[
                    PreviewSection(
                        id="affected_files",
                        title="Affected Files",
                        lines=[str(snapshot.properties.get("attached_script_path"))],
                    ),
                    PreviewSection(
                        id="preview_changes",
                        title="Preview Changes",
                        lines=[
                            "Add placeholder jump counter state.",
                            "Insert a second-jump branch guarded by TODO comments.",
                        ],
                    ),
                    PreviewSection(
                        id="execution_boundary",
                        title="Execution Boundary",
                        lines=[
                            "Core returns a preview patch only.",
                            "Plugin must keep actual editor mutation local and confirm before apply.",
                        ],
                        style="note",
                    ),
                ],
                confirmation_details=ConfirmationDetails(
                    reason=(
                        "This preview targets an attached script and outlines a local scaffold "
                        "the plugin would later apply inside the editor."
                    ),
                    review_items=[
                        "Confirm the attached script path is the intended target.",
                        "Review the placeholder jump counter state before apply.",
                        "Review the guarded second-jump branch and TODO markers before apply.",
                    ],
                ),
                engine_mutations=["none: plan preview only; plugin execution required"],
                rollback_strategy=(
                    "Do not apply automatically. Remove the scaffolded method and state "
                    "additions if the user later rejects the plan."
                ),
            )
        return None

    def patch(self, snapshot: ObjectSnapshot, action_id: str | None) -> PatchProposal | None:
        if action_id == "add_double_jump_scaffold" and snapshot.type_name == "CharacterBody3D" and self._has_script(snapshot):
            return PatchProposal(
                patch_id=f"patch_add_double_jump_scaffold_{snapshot.object_id}",
                action_id="add_double_jump_scaffold",
                patch_kind="script_scaffold",
                target_id=snapshot.object_id,
                target_path=str(snapshot.properties.get("attached_script_path")),
                format="text/x-gdscript",
                content=(
                    "# TODO(anchor_agent): add double-jump state\n"
                    "var jump_count := 0\n"
                    "var max_jump_count := 2\n"
                ),
                apply_mode="plugin_local_preview_only",
            )
        if action_id == "validate_movement_setup" and snapshot.type_name == "CharacterBody3D":
            return PatchProposal(
                patch_id=f"patch_validate_movement_setup_{snapshot.object_id}",
                action_id="validate_movement_setup",
                patch_kind="validation_note",
                target_id=snapshot.object_id,
                target_path="",
                format="application/json",
                content="{\"note\":\"Validation preview only; no file mutation proposed.\"}",
                apply_mode="preview_only",
            )
        if action_id == "review_collision_shape_setup" and snapshot.type_name == "CharacterBody3D" and not self._has_collision_shape(snapshot):
            return PatchProposal(
                patch_id=f"patch_review_collision_shape_setup_{snapshot.object_id}",
                action_id="review_collision_shape_setup",
                patch_kind="validation_note",
                target_id=snapshot.object_id,
                target_path="",
                format="application/json",
                content="{\"note\":\"Collision capability is missing; keep any fix local to the plugin/editor.\"}",
                apply_mode="preview_only",
            )
        return None

    @staticmethod
    def _has_script(snapshot: ObjectSnapshot) -> bool:
        return "has_script" in snapshot.capabilities or bool(snapshot.properties.get("attached_script_path"))

    @staticmethod
    def _has_collision_shape(snapshot: ObjectSnapshot) -> bool:
        return "has_collision_shape" in snapshot.capabilities or bool(snapshot.properties.get("has_collision_shape"))
