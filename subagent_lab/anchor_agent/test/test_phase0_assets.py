from __future__ import annotations

import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from anchor_agent.anchor_agent_core.app.server import create_app
from anchor_agent.anchor_agent_core.domain.planner import RuleBasedPlanner
from anchor_agent.anchor_agent_core.ir.action_plan import ActionPlan
from anchor_agent.anchor_agent_core.ir.object_snapshot import ObjectSnapshot


class AnchorAgentPhase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.anchor_root = Path(__file__).resolve().parents[1]
        self.fixtures_root = self.anchor_root / "test_fixtures"

    def _load_json(self, *parts: str):
        with (self.fixtures_root.joinpath(*parts)).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_protocol_doc_exists(self) -> None:
        protocol_doc = self.anchor_root / "docs" / "protocol-v0_1.md"
        self.assertTrue(protocol_doc.exists())
        text = protocol_doc.read_text(encoding="utf-8")
        self.assertIn('"protocol_version": "0.1"', text)
        self.assertIn("POST /v1/actions/suggest", text)

    def test_snapshot_fixtures_cover_required_fields(self) -> None:
        required_keys = {
            "object_id",
            "engine",
            "object_kind",
            "display_name",
            "type_name",
            "path",
            "scene_path",
            "parent_id",
            "properties",
            "relations",
            "diagnostics",
            "capabilities",
            "selection_state",
        }
        for fixture_name in [
            "character_body_3d_with_script.json",
            "character_body_3d_without_script.json",
            "character_body_3d_missing_collision_shape.json",
            "plain_node_3d.json",
            "camera_3d.json",
        ]:
            payload = self._load_json("snapshots", fixture_name)
            self.assertEqual(required_keys, set(payload.keys()))

    def test_planner_matches_golden_suggest_fixture(self) -> None:
        planner = RuleBasedPlanner()
        snapshot = ObjectSnapshot.model_validate(
            self._load_json("snapshots", "character_body_3d_with_script.json")
        )
        actual = [item.model_dump(mode="json") for item in planner.suggest(snapshot)]
        expected = self._load_json("actions", "character_body_3d_with_script.suggest.json")
        self.assertEqual(expected, actual)

    def test_planner_matches_missing_collision_golden_fixtures(self) -> None:
        planner = RuleBasedPlanner()
        snapshot = ObjectSnapshot.model_validate(
            self._load_json("snapshots", "character_body_3d_missing_collision_shape.json")
        )
        actual_suggest = [item.model_dump(mode="json") for item in planner.suggest(snapshot)]
        actual_explain = planner.explain(snapshot, "review_collision_shape_setup")
        actual_plan = planner.plan(snapshot, "review_collision_shape_setup")
        actual_patch = planner.patch(snapshot, "review_collision_shape_setup")
        expected_suggest = self._load_json(
            "actions",
            "character_body_3d_missing_collision_shape.suggest.json",
        )
        expected_explain = self._load_json(
            "actions",
            "character_body_3d_missing_collision_shape.review_collision_shape_setup.explain.json",
        )
        expected_plan = self._load_json(
            "plans",
            "character_body_3d_missing_collision_shape.review_collision_shape_setup.plan.json",
        )
        expected_patch = self._load_json(
            "patches",
            "character_body_3d_missing_collision_shape.review_collision_shape_setup.patch.json",
        )
        self.assertEqual(expected_suggest, actual_suggest)
        self.assertEqual(expected_explain, actual_explain)
        self.assertEqual(expected_plan, actual_plan.model_dump(mode="json"))
        self.assertEqual(expected_patch, actual_patch.model_dump(mode="json"))

    def test_planner_matches_golden_explain_fixture(self) -> None:
        planner = RuleBasedPlanner()
        snapshot = ObjectSnapshot.model_validate(
            self._load_json("snapshots", "character_body_3d_with_script.json")
        )
        actual = planner.explain(snapshot, "add_double_jump_scaffold")
        expected = self._load_json(
            "actions",
            "character_body_3d_with_script.add_double_jump_scaffold.explain.json",
        )
        self.assertEqual(expected, actual)

    def test_planner_matches_golden_plan_and_patch_fixtures(self) -> None:
        planner = RuleBasedPlanner()
        snapshot = ObjectSnapshot.model_validate(
            self._load_json("snapshots", "character_body_3d_with_script.json")
        )
        actual_plan = planner.plan(snapshot, "add_double_jump_scaffold")
        actual_patch = planner.patch(snapshot, "add_double_jump_scaffold")
        expected_plan = self._load_json(
            "plans",
            "character_body_3d_with_script.add_double_jump_scaffold.plan.json",
        )
        expected_patch = self._load_json(
            "patches",
            "character_body_3d_with_script.add_double_jump_scaffold.patch.json",
        )
        self.assertEqual(expected_plan, actual_plan.model_dump(mode="json"))
        self.assertEqual(expected_patch, actual_patch.model_dump(mode="json"))

    def test_core_api_plan_includes_preview_sections(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_with_script.json")
        client = TestClient(create_app())

        session_id = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open_for_plan",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        ).json()["data"]["session_id"]

        client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert_for_plan",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )

        plan_response = client.post(
            "/v1/actions/plan",
            json={
                "protocol_version": "0.1",
                "request_id": "req_plan",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {
                    "object_id": "node_player",
                    "action_id": "add_double_jump_scaffold",
                },
            },
        )
        self.assertEqual(200, plan_response.status_code)
        preview_sections = plan_response.json()["data"]["plan"]["preview_sections"]
        self.assertEqual(
            ["affected_files", "preview_changes", "execution_boundary"],
            [section["id"] for section in preview_sections],
        )

    def test_core_api_plan_includes_confirmation_details(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_with_script.json")
        client = TestClient(create_app())

        session_id = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open_for_confirmation",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        ).json()["data"]["session_id"]

        client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert_for_confirmation",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )

        plan_response = client.post(
            "/v1/actions/plan",
            json={
                "protocol_version": "0.1",
                "request_id": "req_confirmation_plan",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {
                    "object_id": "node_player",
                    "action_id": "add_double_jump_scaffold",
                },
            },
        )
        self.assertEqual(200, plan_response.status_code)
        confirmation_details = plan_response.json()["data"]["plan"]["confirmation_details"]
        self.assertEqual(
            "This preview targets an attached script and outlines a local scaffold the plugin would later apply inside the editor.",
            confirmation_details["reason"],
        )
        self.assertEqual(
            [
                "Confirm the attached script path is the intended target.",
                "Review the placeholder jump counter state before apply.",
                "Review the guarded second-jump branch and TODO markers before apply.",
            ],
            confirmation_details["review_items"],
        )

    def test_action_plan_requires_confirmation_details_when_confirmation_is_true(self) -> None:
        with self.assertRaises(ValidationError):
            ActionPlan(
                action_id="missing_confirmation_details",
                summary="Preview a confirmation-required change without structured details.",
                risk="medium",
                requires_confirmation=True,
                steps=["Review the preview carefully."],
                affected_objects=["node_player"],
                affected_files=["res://player.gd"],
                preview_changes=["Would add a guarded second jump branch."],
                preview_sections=[],
                engine_mutations=["none: preview only"],
                rollback_strategy="No apply performed.",
            )

    def test_core_api_rejects_direct_execution_request(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_with_script.json")
        client = TestClient(create_app())

        session_id = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open_for_boundary",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        ).json()["data"]["session_id"]

        client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert_for_boundary",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )

        plan_response = client.post(
            "/v1/actions/plan",
            json={
                "protocol_version": "0.1",
                "request_id": "req_boundary",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {
                    "object_id": "node_player",
                    "action_id": "add_double_jump_scaffold",
                    "execution_intent": "apply",
                    "allow_core_execution": True,
                },
            },
        )
        self.assertEqual(400, plan_response.status_code)
        payload = plan_response.json()
        self.assertEqual("EXECUTION_BOUNDARY_VIOLATION", payload["error"]["code"])
        self.assertEqual("apply", payload["error"]["details"]["execution_intent"])

    def test_core_api_requests_clarification_for_ambiguous_execution_intent(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_with_script.json")
        client = TestClient(create_app())

        session_id = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open_for_clarification",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        ).json()["data"]["session_id"]

        client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert_for_clarification",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )

        plan_response = client.post(
            "/v1/actions/plan",
            json={
                "protocol_version": "0.1",
                "request_id": "req_clarification",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {
                    "object_id": "node_player",
                    "action_id": "add_double_jump_scaffold",
                    "execution_intent": "preview_or_execute",
                },
            },
        )
        self.assertEqual(400, plan_response.status_code)
        payload = plan_response.json()
        self.assertEqual("REQUEST_CLARIFICATION_REQUIRED", payload["error"]["code"])
        self.assertEqual("execution_mode", payload["error"]["details"]["clarification_topic"])
        self.assertEqual("preview_or_execute", payload["error"]["details"]["execution_intent"])

    def test_plugin_shell_files_exist(self) -> None:
        plugin_root = self.anchor_root / "anchor_agent_godot_plugin" / "addons" / "anchor_agent"
        expected_files = [
            plugin_root / "plugin.cfg",
            plugin_root / "plugin.gd",
            plugin_root / "ui" / "agent_dock.tscn",
            plugin_root / "ui" / "agent_dock.gd",
            plugin_root / "transport" / "core_client.gd",
            plugin_root / "adapters" / "selection_adapter.gd",
            plugin_root / "adapters" / "snapshot_builder.gd",
        ]
        for path in expected_files:
            self.assertTrue(path.exists(), str(path))

        plugin_cfg = (plugin_root / "plugin.cfg").read_text(encoding="utf-8")
        self.assertIn('script="plugin.gd"', plugin_cfg)
        self.assertNotIn('script="res://', plugin_cfg)

    def test_plugin_dock_mentions_preview_sections(self) -> None:
        dock_script = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "ui"
            / "agent_dock.gd"
        )
        text = dock_script.read_text(encoding="utf-8")
        self.assertIn("show_plan_payload", text)
        self.assertIn("preview_sections", text)
        self.assertIn("requires_confirmation", text)
        self.assertIn("confirmation_details", text)
        self.assertIn("review_items", text)
        self.assertIn("Confirmation Required:", text)
        self.assertIn("Review Before Apply:", text)
        self.assertIn("Review this preview before any editor-side apply.", text)

    def test_plugin_empty_state_copy_is_descriptive(self) -> None:
        dock_script = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "ui"
            / "agent_dock.gd"
        )
        dock_scene = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "ui"
            / "agent_dock.tscn"
        )
        script_text = dock_script.read_text(encoding="utf-8")
        scene_text = dock_scene.read_text(encoding="utf-8")
        self.assertIn("EMPTY_TARGET_SUMMARY", script_text)
        self.assertIn("EMPTY_PREVIEW_TEXT", script_text)
        self.assertIn("Anchor Agent Preview", scene_text)
        self.assertIn("Select a node to inspect its context and suggested actions.", scene_text)
        self.assertIn("Choose an action to review a preview plan before any editor-side change.", scene_text)

    def test_snapshot_builder_mentions_collision_shape_capability(self) -> None:
        builder_script = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "adapters"
            / "snapshot_builder.gd"
        )
        text = builder_script.read_text(encoding="utf-8")
        self.assertIn("has_collision_shape", text)
        self.assertIn("_has_collision_shape_child", text)

    def test_plugin_selection_lifecycle_wiring_exists(self) -> None:
        plugin_script = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "plugin.gd"
        )
        dock_script = (
            self.anchor_root
            / "anchor_agent_godot_plugin"
            / "addons"
            / "anchor_agent"
            / "ui"
            / "agent_dock.gd"
        )
        plugin_text = plugin_script.read_text(encoding="utf-8")
        dock_text = dock_script.read_text(encoding="utf-8")
        self.assertIn("SelectionAdapter", plugin_text)
        self.assertIn("SnapshotBuilder", plugin_text)
        self.assertIn("selection_changed", plugin_text)
        self.assertIn("_refresh_selection_state", plugin_text)
        self.assertIn("reset_for_empty_selection", plugin_text)
        self.assertIn("show_selected_snapshot", plugin_text)
        self.assertIn("show_selected_snapshot", dock_text)
        self.assertIn("reset_for_empty_selection", dock_text)
        self.assertIn("Selected:", dock_text)
        self.assertIn("Path:", dock_text)

    def test_core_api_smoke_open_context_and_suggest(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_with_script.json")
        client = TestClient(create_app())

        open_response = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        )
        self.assertEqual(200, open_response.status_code)
        session_id = open_response.json()["data"]["session_id"]

        upsert_response = client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )
        self.assertEqual(200, upsert_response.status_code)
        self.assertEqual(1, upsert_response.json()["data"]["snapshot_count"])

        suggest_response = client.post(
            "/v1/actions/suggest",
            json={
                "protocol_version": "0.1",
                "request_id": "req_suggest",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"object_id": "node_player"},
            },
        )
        self.assertEqual(200, suggest_response.status_code)
        action_ids = [item["id"] for item in suggest_response.json()["data"]["actions"]]
        self.assertEqual(
            ["validate_movement_setup", "add_double_jump_scaffold"],
            action_ids,
        )

    def test_core_api_suggests_collision_review_when_capability_missing(self) -> None:
        snapshot = self._load_json("snapshots", "character_body_3d_missing_collision_shape.json")
        client = TestClient(create_app())

        session_id = client.post(
            "/v1/session/open",
            json={
                "protocol_version": "0.1",
                "request_id": "req_open_missing_collision",
                "session_id": None,
                "project_id": "godot_demo",
                "payload": {},
            },
        ).json()["data"]["session_id"]

        client.post(
            "/v1/context/upsert",
            json={
                "protocol_version": "0.1",
                "request_id": "req_upsert_missing_collision",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"snapshots": [snapshot]},
            },
        )

        suggest_response = client.post(
            "/v1/actions/suggest",
            json={
                "protocol_version": "0.1",
                "request_id": "req_suggest_missing_collision",
                "session_id": session_id,
                "project_id": "godot_demo",
                "payload": {"object_id": "node_ghost_player"},
            },
        )
        self.assertEqual(200, suggest_response.status_code)
        action_ids = [item["id"] for item in suggest_response.json()["data"]["actions"]]
        self.assertEqual(
            ["validate_movement_setup", "review_collision_shape_setup"],
            action_ids,
        )
