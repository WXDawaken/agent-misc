from __future__ import annotations

from dataclasses import dataclass
import json
import unittest

from game_engine import (
    CommandArgumentSpec,
    CommandSpec,
    Position,
    RectGrid,
    REQUIRED_RENDER_THEME_SLOTS,
    RenderTheme,
    RenderThemeSlot,
    ReplaySession,
    ReplayStep,
    Snapshot,
    SnapshotActor,
    SnapshotAnnotation,
    SnapshotLayer,
    SnapshotPosition,
    SnapshotSize,
    export_command_manifest,
    parse_command,
    push_capped_message,
    render_rect_grid,
    run_command_replay,
)
from game_engine.commands import normalize_cardinal_token, normalize_command_token


_DIRECTION_ARG = CommandArgumentSpec(
    name="dir",
    choices=("w", "a", "s", "d"),
    hint="w|a|s|d",
)

_COMMAND_SPECS = (
    CommandSpec(
        command_id="move_north",
        primary_token="w",
        label="Move Up",
        description="move",
        aliases=("up",),
        hotkeys=("W", "Up"),
        category="movement",
    ),
    CommandSpec(
        command_id="dash",
        primary_token="dash",
        label="Dash",
        description="lunges two tiles for extra energy but can smash your hull",
        args=(_DIRECTION_ARG,),
    ),
    CommandSpec(
        command_id="help",
        primary_token="help",
        label="Help",
        description="repeats this text",
        aliases=("h", "?"),
        hotkeys=("H", "?"),
    ),
)


@dataclass
class _ReplayState:
    value: int = 0
    status: str = "playing"


def _snapshot_replay_state(state: _ReplayState) -> Snapshot:
    return Snapshot(
        board=SnapshotSize(width=1, height=1),
        layers=(),
        hud={"value": state.value},
        status=state.status,
        terminal=state.status != "playing",
    )


def _apply_replay_command(state: _ReplayState, raw_command: str) -> None:
    if raw_command == "advance":
        state.value += 1
        return
    if raw_command == "stop":
        state.value += 1
        state.status = "won"
        return
    if raw_command == "lose":
        state.status = "lost"
        return
    raise AssertionError(f"Unexpected replay command {raw_command!r}")


class GameEngineTests(unittest.TestCase):
    def test_position_helpers_support_grid_movement(self) -> None:
        position = Position(2, 3)
        self.assertEqual(position.moved(-1, 2), Position(1, 5))
        self.assertEqual(position.manhattan(Position(5, 1)), 5)

    def test_render_rect_grid_renders_row_major_ascii_output(self) -> None:
        rendered = render_rect_grid(
            3,
            2,
            lambda position: "#" if position == Position(1, 0) else ".",
            separator=" ",
        )
        self.assertEqual(rendered, ". # .\n. . .")

    def test_render_theme_exports_required_slots_and_legend_metadata(self) -> None:
        theme = RenderTheme(
            theme_id="emoji",
            title="Emoji",
            slots=(
                RenderThemeSlot("empty", "⬛", "empty"),
                RenderThemeSlot("player", "🙂", "you"),
                RenderThemeSlot("drone", "🤖", "drone"),
                RenderThemeSlot("salvage", "💎", "salvage"),
                RenderThemeSlot("hazard", "🔥", "hazard", "Terminal width may vary by font."),
                RenderThemeSlot("wall", "🧱", "wall"),
                RenderThemeSlot("exit", "🚪", "exit"),
            ),
            legend_order=("player", "drone", "salvage", "hazard", "wall", "exit"),
            notes=(
                "Emoji and full-width glyphs may misalign in terminals without Unicode-width support.",
            ),
        )

        payload = theme.to_dict()

        self.assertEqual(
            payload,
            {
                "id": "emoji",
                "title": "Emoji",
                "slots": [
                    {"id": "empty", "token": "⬛", "label": "empty"},
                    {"id": "player", "token": "🙂", "label": "you"},
                    {"id": "drone", "token": "🤖", "label": "drone"},
                    {"id": "salvage", "token": "💎", "label": "salvage"},
                    {
                        "id": "hazard",
                        "token": "🔥",
                        "label": "hazard",
                        "description": "Terminal width may vary by font.",
                    },
                    {"id": "wall", "token": "🧱", "label": "wall"},
                    {"id": "exit", "token": "🚪", "label": "exit"},
                ],
                "legend": [
                    {"id": "player", "token": "🙂", "label": "you"},
                    {"id": "drone", "token": "🤖", "label": "drone"},
                    {"id": "salvage", "token": "💎", "label": "salvage"},
                    {
                        "id": "hazard",
                        "token": "🔥",
                        "label": "hazard",
                        "description": "Terminal width may vary by font.",
                    },
                    {"id": "wall", "token": "🧱", "label": "wall"},
                    {"id": "exit", "token": "🚪", "label": "exit"},
                ],
                "notes": [
                    "Emoji and full-width glyphs may misalign in terminals without Unicode-width support.",
                ],
            },
        )
        self.assertEqual(theme.legend_slots[0].slot_id, "player")
        self.assertEqual(theme.token_for("exit"), "🚪")
        self.assertEqual(REQUIRED_RENDER_THEME_SLOTS[-1], "exit")
        self.assertIsInstance(json.dumps(payload), str)

    def test_render_theme_requires_complete_unique_slot_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required slots"):
            RenderTheme(
                theme_id="ascii",
                slots=(
                    RenderThemeSlot("empty", ".", "empty"),
                    RenderThemeSlot("player", "@", "you"),
                    RenderThemeSlot("drone", "D", "drone"),
                    RenderThemeSlot("salvage", "$", "salvage"),
                    RenderThemeSlot("hazard", "!", "hazard"),
                    RenderThemeSlot("wall", "#", "wall"),
                ),
            )

        with self.assertRaisesRegex(ValueError, "Duplicate render theme slot"):
            RenderTheme(
                theme_id="broken",
                slots=(
                    RenderThemeSlot("empty", ".", "empty"),
                    RenderThemeSlot("player", "@", "you"),
                    RenderThemeSlot("player", "P", "pilot"),
                    RenderThemeSlot("drone", "D", "drone"),
                    RenderThemeSlot("salvage", "$", "salvage"),
                    RenderThemeSlot("hazard", "!", "hazard"),
                    RenderThemeSlot("wall", "#", "wall"),
                    RenderThemeSlot("exit", "E", "exit"),
                ),
            )

        with self.assertRaisesRegex(ValueError, "Legend slot 'missing' is not defined"):
            RenderTheme(
                theme_id="bad-legend",
                slots=(
                    RenderThemeSlot("empty", ".", "empty"),
                    RenderThemeSlot("player", "@", "you"),
                    RenderThemeSlot("drone", "D", "drone"),
                    RenderThemeSlot("salvage", "$", "salvage"),
                    RenderThemeSlot("hazard", "!", "hazard"),
                    RenderThemeSlot("wall", "#", "wall"),
                    RenderThemeSlot("exit", "E", "exit"),
                ),
                legend_order=("player", "missing"),
            )

    def test_push_capped_message_keeps_recent_tail(self) -> None:
        messages = ["old-1", "old-2"]
        for index in range(7):
            push_capped_message(messages, f"event-{index}", limit=4)
        self.assertEqual(messages, ["event-3", "event-4", "event-5", "event-6"])

    def test_direction_normalizer_handles_cardinal_aliases(self) -> None:
        self.assertEqual(normalize_cardinal_token("UP"), "w")
        self.assertEqual(normalize_cardinal_token("right"), "d")
        self.assertEqual(normalize_cardinal_token("repair"), "repair")

    def test_command_normalizer_uses_manifest_aliases(self) -> None:
        self.assertEqual(normalize_command_token("UP", _COMMAND_SPECS), "w")
        self.assertEqual(normalize_command_token("?", _COMMAND_SPECS), "help")
        self.assertEqual(normalize_command_token("dash", _COMMAND_SPECS), "dash")

    def test_parse_command_normalizes_manifest_command_and_argument_tokens(self) -> None:
        self.assertEqual(parse_command("h", _COMMAND_SPECS), ("help", []))
        self.assertEqual(parse_command("DASH right", _COMMAND_SPECS), ("dash", ["d"]))
        self.assertEqual(parse_command("dash east", _COMMAND_SPECS), ("dash", ["east"]))
        self.assertEqual(parse_command("  ", _COMMAND_SPECS), ("", []))

    def test_command_manifest_export_is_json_serializable(self) -> None:
        manifest = export_command_manifest(_COMMAND_SPECS)

        self.assertEqual(
            manifest,
            [
                {
                    "id": "move_north",
                    "primary_token": "w",
                    "description": "move",
                    "usage": "w",
                    "label": "Move Up",
                    "aliases": ["up"],
                    "hotkeys": ["W", "Up"],
                    "category": "movement",
                },
                {
                    "id": "dash",
                    "primary_token": "dash",
                    "description": "lunges two tiles for extra energy but can smash your hull",
                    "usage": "dash <dir>",
                    "label": "Dash",
                    "args": [
                        {
                            "name": "dir",
                            "required": True,
                            "choices": ["w", "a", "s", "d"],
                            "hint": "w|a|s|d",
                        }
                    ],
                },
                {
                    "id": "help",
                    "primary_token": "help",
                    "description": "repeats this text",
                    "usage": "help",
                    "label": "Help",
                    "aliases": ["h", "?"],
                    "hotkeys": ["H", "?"],
                },
            ],
        )
        self.assertIsInstance(json.dumps(manifest), str)

    def test_snapshot_annotations_are_json_serializable_and_deterministic(self) -> None:
        snapshot = Snapshot(
            board=SnapshotSize(width=5, height=4),
            layers=(),
            annotations=(
                SnapshotAnnotation.from_position(
                    Position(3, 2),
                    terrain_tags=("salvage", "loot"),
                    actor_tags=("player",),
                    overlay_flags=("selected", "highlight"),
                    values={
                        "distance": 2,
                        "inspector": {"summary": "cache", "priority": 1},
                    },
                ),
                SnapshotAnnotation.from_position(Position(1, 0), values={}),
                SnapshotAnnotation.from_position(
                    Position(0, 1),
                    terrain_tags=("hazard",),
                    overlay_flags=("threat", "pulse"),
                    values={"radius": 3, "sources": ("drone-2", "drone-1")},
                ),
            ),
        )

        payload = snapshot.to_dict()

        self.assertEqual(
            payload,
            {
                "board": {"width": 5, "height": 4},
                "layers": [],
                "actors": [],
                "messages": [],
                "hud": {},
                "status": "playing",
                "terminal": False,
                "annotations": [
                    {"position": {"x": 0, "y": 1}, "terrain_tags": ["hazard"], "overlay_flags": ["pulse", "threat"], "values": {"radius": 3, "sources": ["drone-2", "drone-1"]}},
                    {"position": {"x": 1, "y": 0}},
                    {
                        "position": {"x": 3, "y": 2},
                        "terrain_tags": ["loot", "salvage"],
                        "actor_tags": ["player"],
                        "overlay_flags": ["highlight", "selected"],
                        "values": {
                            "distance": 2,
                            "inspector": {"priority": 1, "summary": "cache"},
                        },
                    },
                ],
            },
        )
        self.assertIsInstance(json.dumps(payload), str)

    def test_snapshot_contract_is_json_serializable_and_deterministic(self) -> None:
        snapshot = Snapshot(
            board=SnapshotSize(width=5, height=4),
            layers=(
                SnapshotLayer.from_positions("walls", {Position(4, 1), Position(0, 0)}),
                SnapshotLayer.from_positions("hazards", [Position(2, 3)]),
                SnapshotLayer.from_positions("salvage", {Position(3, 2), Position(1, 2)}),
                SnapshotLayer.from_positions("exit", [Position(4, 3)]),
            ),
            actors=(
                SnapshotActor.from_position(
                    "player",
                    "player",
                    Position(1, 1),
                    values={"energy": 9, "tags": ("scanned", "shielded")},
                ),
                SnapshotActor.from_position("drone-1", "drone", Position(3, 1)),
            ),
            messages=("Scanners sweep the corridor.", "Drone motors spike nearby."),
            hud={
                "energy": 9,
                "hull": {"current": 2, "max": 3},
                "salvage_progress": {"collected": 1, "required": 2},
                "score": 146,
                "turn": 7,
            },
            status="playing",
            terminal=False,
        )

        payload = snapshot.to_dict()

        self.assertNotIn("annotations", payload)
        self.assertEqual(
            payload,
            {
                "board": {"width": 5, "height": 4},
                "layers": [
                    {
                        "name": "walls",
                        "positions": [{"x": 0, "y": 0}, {"x": 4, "y": 1}],
                    },
                    {
                        "name": "hazards",
                        "positions": [{"x": 2, "y": 3}],
                    },
                    {
                        "name": "salvage",
                        "positions": [{"x": 1, "y": 2}, {"x": 3, "y": 2}],
                    },
                    {
                        "name": "exit",
                        "positions": [{"x": 4, "y": 3}],
                    },
                ],
                "actors": [
                    {
                        "id": "player",
                        "kind": "player",
                        "position": {"x": 1, "y": 1},
                        "values": {"energy": 9, "tags": ["scanned", "shielded"]},
                    },
                    {
                        "id": "drone-1",
                        "kind": "drone",
                        "position": {"x": 3, "y": 1},
                    },
                ],
                "messages": [
                    "Scanners sweep the corridor.",
                    "Drone motors spike nearby.",
                ],
                "hud": {
                    "energy": 9,
                    "hull": {"current": 2, "max": 3},
                    "salvage_progress": {"collected": 1, "required": 2},
                    "score": 146,
                    "turn": 7,
                },
                "status": "playing",
                "terminal": False,
            },
        )
        self.assertIsInstance(json.dumps(payload), str)

    def test_snapshot_helpers_bridge_existing_grid_primitives(self) -> None:
        grid = RectGrid(name="test", width=4, height=3, walls=frozenset())

        self.assertEqual(SnapshotSize.from_grid(grid), SnapshotSize(width=4, height=3))
        self.assertEqual(
            SnapshotPosition.from_position(Position(2, 1)),
            SnapshotPosition(x=2, y=1),
        )

    def test_run_command_replay_records_initial_and_per_step_snapshots(self) -> None:
        session = run_command_replay(
            _ReplayState(),
            ["advance", "stop", "advance"],
            _apply_replay_command,
            _snapshot_replay_state,
        )

        self.assertEqual(
            session,
            ReplaySession(
                initial_snapshot=Snapshot(
                    board=SnapshotSize(width=1, height=1),
                    layers=(),
                    hud={"value": 0},
                    status="playing",
                    terminal=False,
                ),
                steps=(
                    ReplayStep(
                        raw_command="advance",
                        snapshot=Snapshot(
                            board=SnapshotSize(width=1, height=1),
                            layers=(),
                            hud={"value": 1},
                            status="playing",
                            terminal=False,
                        ),
                        status="playing",
                        terminal=False,
                    ),
                    ReplayStep(
                        raw_command="stop",
                        snapshot=Snapshot(
                            board=SnapshotSize(width=1, height=1),
                            layers=(),
                            hud={"value": 2},
                            status="won",
                            terminal=True,
                        ),
                        status="won",
                        terminal=True,
                    ),
                ),
                final_snapshot=Snapshot(
                    board=SnapshotSize(width=1, height=1),
                    layers=(),
                    hud={"value": 2},
                    status="won",
                    terminal=True,
                ),
                terminal_status="won",
                terminal=True,
            ),
        )
        self.assertIsInstance(json.dumps(session.to_dict()), str)

    def test_run_command_replay_short_circuits_terminal_initial_state(self) -> None:
        session = run_command_replay(
            _ReplayState(value=4, status="lost"),
            ["advance"],
            _apply_replay_command,
            _snapshot_replay_state,
        )

        self.assertEqual(session.steps, ())
        self.assertEqual(session.final_snapshot.hud, {"value": 4})
        self.assertEqual(session.terminal_status, "lost")
        self.assertTrue(session.terminal)


if __name__ == "__main__":
    unittest.main()
