from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from game_engine import CommandSpec, RenderTheme, run_command_replay
from salvage_run import __main__ as cli
from salvage_run.commands import COMMAND_MANIFEST, COMMAND_SPECS, HELP_TEXT, parse_command
from salvage_run.engine import apply_command
from salvage_run.levels import build_level
from salvage_run.models import GameState, Position
from salvage_run.snapshot import snapshot_state
from salvage_run import ui as render_ui
from salvage_run.ui import render_game


TEST_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SalvageRunTests(unittest.TestCase):
    def test_level_selection_is_repeatable(self) -> None:
        level_a = build_level(seed=4)
        level_b = build_level(seed=4)
        self.assertEqual(level_a, level_b)

    def test_invalid_move_does_not_spend_energy(self) -> None:
        state = GameState.new(build_level(seed=0))
        apply_command(state, "a")
        self.assertEqual(state.player, Position(0, 0))
        self.assertEqual(state.energy, 18)

    def test_extra_tokens_do_not_bypass_command_validation(self) -> None:
        state = GameState.new(build_level(seed=0))
        apply_command(state, "d extra")
        self.assertEqual(state.player, Position(0, 0))
        self.assertEqual(state.energy, 18)
        self.assertIn("Unknown command", " ".join(state.messages))

    def test_help_text_is_generated_from_manifest(self) -> None:
        self.assertEqual(
            HELP_TEXT,
            "Commands: w/a/s/d move, scan reports the nearest salvage, the nearest drone, and how many drones can chase you, "
            "dash <dir> lunges two tiles for extra energy but can smash your hull, "
            "repair spends energy to restore hull, wait skips a turn, help repeats this text, "
            "quit exits the run.",
        )
        self.assertEqual(COMMAND_MANIFEST[5]["usage"], "dash <dir>")
        self.assertEqual(COMMAND_MANIFEST[0]["primary_token"], "w")
        self.assertIsInstance(COMMAND_SPECS[0], CommandSpec)
        self.assertEqual(COMMAND_SPECS[8].aliases, ("h", "?"))

    def test_manifest_parser_preserves_shortcuts_and_direction_aliases(self) -> None:
        self.assertEqual(parse_command("h"), ("help", []))
        self.assertEqual(parse_command("?"), ("help", []))
        self.assertEqual(parse_command("."), ("wait", []))
        self.assertEqual(parse_command("r"), ("repair", []))
        self.assertEqual(parse_command("dash right"), ("dash", ["d"]))

    def test_collecting_salvage_updates_state(self) -> None:
        state = GameState.new(build_level(seed=0))
        apply_command(state, "s")
        apply_command(state, "d")
        self.assertEqual(state.player, Position(1, 1))
        apply_command(state, "s")
        self.assertEqual(state.player, Position(1, 2))
        self.assertEqual(state.salvage_collected, 1)
        self.assertNotIn(Position(1, 2), state.salvage_remaining)

    def test_distant_drones_hold_their_patrol_posts(self) -> None:
        state = GameState.new(build_level(seed=0))
        before = sorted(state.drones)
        apply_command(state, "wait")
        after = sorted(state.drones)
        self.assertEqual(after, before)

    def test_nearby_drone_still_chases_player(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.drones = [Position(2, 0)]
        apply_command(state, "wait")
        self.assertEqual(state.drones, [Position(1, 0)])

    def test_scan_reports_when_nearest_drone_is_in_chase_range(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(0, 0)
        state.drones = [Position(4, 0)]

        apply_command(state, "scan")

        self.assertIn(
            "Nearest drone is 4 steps away at (4, 0). It's close enough to start chasing you.",
            state.messages,
        )
        self.assertIn("1 drone is currently in chase range.", state.messages)

    def test_scan_does_not_claim_chase_range_when_drone_is_too_far(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(0, 0)
        state.drones = [Position(5, 0)]

        apply_command(state, "scan")

        self.assertIn(
            "Nearest drone is 5 steps away at (5, 0). It's still too far away to start chasing you.",
            state.messages,
        )
        self.assertIn("0 drones are currently in chase range.", state.messages)

    def test_scan_reports_total_chase_range_drones(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(0, 0)
        state.drones = [Position(4, 0), Position(3, 0), Position(5, 0)]

        apply_command(state, "scan")

        self.assertIn(
            "Nearest drone is 3 steps away at (3, 0). It's close enough to start chasing you.",
            state.messages,
        )
        self.assertIn("2 drones are currently in chase range.", state.messages)

    def test_displaced_drone_returns_toward_its_own_patrol_post(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.drones = [Position(3, 6)]
        apply_command(state, "wait")
        self.assertEqual(state.drones, [Position(3, 5)])

    def test_exit_requires_salvage_goal(self) -> None:
        state = GameState.new(build_level(seed=0), energy=50)
        state.player = Position(state.level.exit_position.x - 1, state.level.exit_position.y)
        apply_command(state, "d")
        self.assertEqual(state.status, "playing")
        self.assertIn("still need", " ".join(state.messages))

    def test_quit_sets_terminal_status(self) -> None:
        state = GameState.new(build_level(seed=0))
        apply_command(state, "quit")
        self.assertEqual(state.status, "quit")

    def test_repair_restores_one_hull_and_spends_energy(self) -> None:
        state = GameState.new(build_level(seed=0), energy=10, hull=2, max_hull=3)
        apply_command(state, "repair")
        self.assertEqual(state.hull, 3)
        self.assertEqual(state.energy, 7)
        self.assertEqual(state.turn, 1)

    def test_repair_at_full_hull_does_not_spend_turn(self) -> None:
        state = GameState.new(build_level(seed=0), energy=10, hull=3, max_hull=3)
        apply_command(state, "repair")
        self.assertEqual(state.hull, 3)
        self.assertEqual(state.energy, 10)
        self.assertEqual(state.turn, 0)
        self.assertIn("fully patched", " ".join(state.messages))

    def test_repair_requires_minimum_energy(self) -> None:
        state = GameState.new(build_level(seed=0), energy=2, hull=2, max_hull=3)
        apply_command(state, "repair")
        self.assertEqual(state.hull, 2)
        self.assertEqual(state.energy, 2)
        self.assertEqual(state.turn, 0)
        self.assertIn("at least 3 energy", " ".join(state.messages))

    def test_dash_moves_two_tiles_and_collects_intermediate_salvage(self) -> None:
        state = GameState.new(build_level(seed=0), energy=10)
        state.player = Position(0, 2)
        apply_command(state, "dash d")
        self.assertEqual(state.player, Position(2, 2))
        self.assertEqual(state.energy, 7)
        self.assertEqual(state.turn, 1)
        self.assertEqual(state.salvage_collected, 1)
        self.assertNotIn(Position(1, 2), state.salvage_remaining)

    def test_dash_into_wall_stops_short_and_damages_hull(self) -> None:
        state = GameState.new(build_level(seed=0), energy=10, hull=3, max_hull=3)
        state.player = Position(0, 1)
        apply_command(state, "dash d")
        self.assertEqual(state.player, Position(1, 1))
        self.assertEqual(state.energy, 7)
        self.assertEqual(state.turn, 1)
        self.assertEqual(state.hull, 2)
        self.assertIn("mid-dash", " ".join(state.messages))

    def test_dash_requires_minimum_energy(self) -> None:
        state = GameState.new(build_level(seed=0), energy=2)
        apply_command(state, "dash d")
        self.assertEqual(state.player, Position(0, 0))
        self.assertEqual(state.energy, 2)
        self.assertEqual(state.turn, 0)
        self.assertIn("at least 3 energy", " ".join(state.messages))

    def test_score_is_derived_from_state(self) -> None:
        state = GameState.new(build_level(seed=0), energy=10, hull=3, max_hull=3)
        state.salvage_collected = 2
        state.turn = 5
        self.assertEqual(state.score, 2 * 100 + 10 * 5 + 3 * 20 - 5 * 2)

    def test_render_includes_score_in_status_line(self) -> None:
        state = GameState.new(build_level(seed=0), energy=9, hull=2, max_hull=3)
        state.salvage_collected = 1
        state.turn = 4
        rendered = render_game(state)
        self.assertIn(f"Score: {state.score}", rendered)

    def test_render_supports_engine_backed_emoji_theme(self) -> None:
        state = GameState.new(build_level(seed=0))
        rendered = render_game(state, theme="emoji")
        theme = render_ui._resolve_theme("emoji")

        self.assertIsInstance(theme, RenderTheme)
        self.assertEqual(theme.legend_slots[0].slot_id, "player")
        self.assertEqual(
            theme.notes,
            (
                "Emoji and full-width glyphs may misalign in terminals without Unicode-width support.",
            ),
        )
        self.assertIn("Legend: 🙂 you, 🤖 drone, 💎 salvage, 🔥 hazard, 🧱 wall, 🚪 exit", rendered)
        self.assertIn("🙂", rendered)
        self.assertIn("🤖", rendered)
        self.assertIn("💎", rendered)
        self.assertIn("🔥", rendered)
        self.assertIn("🧱", rendered)
        self.assertIn("🚪", rendered)

    def test_render_supports_local_scanner_theme(self) -> None:
        state = GameState.new(build_level(seed=0))
        rendered = render_game(state, theme="scanner")
        theme = render_ui._resolve_theme("scanner")

        self.assertIsInstance(theme, RenderTheme)
        self.assertEqual(
            [slot.slot_id for slot in theme.legend_slots],
            ["player", "salvage", "exit", "drone", "hazard", "wall"],
        )
        self.assertEqual(
            theme.notes,
            (
                "Scanner theme keeps the board ASCII-only with terse objective and threat markers.",
            ),
        )
        self.assertIn(
            "Legend: @ you, + cache, > extract, x contact, ! hazard, = bulkhead",
            rendered,
        )
        self.assertIn("x", rendered)
        self.assertIn("+", rendered)
        self.assertIn("=", rendered)
        self.assertIn(">", rendered)

    def test_scanner_theme_renders_tactical_summary_line_from_snapshot_annotations(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(1, 1)
        state.drones = [Position(4, 1)]
        state.salvage_remaining = {Position(2, 1), Position(6, 6)}
        state.salvage_collected = 2

        rendered = render_game(state, theme="scanner")

        self.assertEqual(
            rendered.splitlines()[1],
            "Scanner: cache 1 away @ (2, 1) | contact 3 away @ (4, 1) | extract LOCKED (1 cache needed)",
        )

    def test_scanner_theme_renders_three_nearest_points_of_interest_strip(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(1, 1)
        state.drones = [Position(4, 1)]
        state.salvage_remaining = {Position(2, 1), Position(6, 6)}
        state.salvage_collected = 2

        rendered = render_game(state, theme="scanner")

        self.assertEqual(
            rendered.splitlines()[2],
            "POI: cache 1 away @ (2, 1) | contact 3 away @ (4, 1) | hazard 5 away @ (6, 1)",
        )

    def test_scanner_theme_marks_ready_extract_and_missing_contacts_in_summary(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(1, 1)
        state.drones = []
        state.salvage_remaining = set()
        state.salvage_collected = state.level.required_salvage

        rendered = render_game(state, theme="scanner")

        self.assertEqual(
            rendered.splitlines()[1],
            "Scanner: cache clear | contact none | extract READY",
        )

    def test_scanner_theme_uses_extract_label_in_points_of_interest_strip(self) -> None:
        state = GameState.new(build_level(seed=0))
        state.player = Position(6, 5)
        state.drones = []
        state.salvage_remaining = set()
        state.salvage_collected = state.level.required_salvage

        rendered = render_game(state, theme="scanner")

        self.assertEqual(
            rendered.splitlines()[2],
            "POI: hazard 1 away @ (5, 5) | extract 3 away @ (7, 7) | hazard 4 away @ (6, 1)",
        )

    def test_ascii_theme_does_not_include_scanner_summary_line(self) -> None:
        state = GameState.new(build_level(seed=0))

        rendered = render_game(state)

        self.assertNotIn("Scanner:", rendered)

    def test_cli_theme_defaults_to_ascii(self) -> None:
        args = cli.parse_args([])
        self.assertEqual(args.theme, render_ui.DEFAULT_THEME)

    def test_cli_accepts_scanner_theme(self) -> None:
        args = cli.parse_args(["--theme", "scanner"])
        self.assertEqual(args.theme, "scanner")

    def test_non_default_theme_reconfigures_output_streams_to_utf8(self) -> None:
        calls: list[tuple[str, str]] = []

        def make_stream(name: str) -> SimpleNamespace:
            return SimpleNamespace(
                reconfigure=lambda **kwargs: calls.append((name, kwargs["encoding"]))
            )

        with patch.object(cli.sys, "stdout", make_stream("stdout")), patch.object(
            cli.sys, "stderr", make_stream("stderr")
        ):
            cli._configure_output_encoding("emoji")

        self.assertEqual(calls, [("stdout", "utf-8"), ("stderr", "utf-8")])

    def test_script_mode_threads_selected_theme_through_rendering(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), patch("sys.stdin", io.StringIO("quit\n")):
            result = cli.main(["--script", "-", "--theme", "emoji"])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Legend: 🙂 you, 🤖 drone, 💎 salvage, 🔥 hazard, 🧱 wall, 🚪 exit", rendered)
        self.assertIn("🙂", rendered)

    def test_render_rejects_unknown_theme(self) -> None:
        state = GameState.new(build_level(seed=0))
        with self.assertRaises(ValueError) as context:
            render_game(state, theme="ansi-art")

        self.assertIn("Unsupported theme", str(context.exception))

    def test_snapshot_state_uses_shared_engine_contract(self) -> None:
        state = GameState.new(build_level(seed=0), energy=9, hull=2, max_hull=4)
        state.player = Position(1, 1)
        state.drones = [Position(3, 3), Position(2, 0)]
        state.salvage_remaining = {Position(6, 0), Position(5, 7)}
        state.salvage_collected = 2
        state.turn = 5
        state.messages = ["Scanners sweep the corridor.", "Drone motors spike nearby."]

        payload = snapshot_state(state).to_dict()

        self.assertEqual(
            payload,
            {
                "board": {"width": 8, "height": 8},
                "layers": [
                    {
                        "name": "walls",
                        "positions": [
                            {"x": 1, "y": 4},
                            {"x": 1, "y": 6},
                            {"x": 2, "y": 1},
                            {"x": 2, "y": 4},
                            {"x": 3, "y": 0},
                            {"x": 4, "y": 2},
                            {"x": 4, "y": 3},
                            {"x": 5, "y": 6},
                            {"x": 7, "y": 5},
                        ],
                    },
                    {
                        "name": "hazards",
                        "positions": [{"x": 5, "y": 5}, {"x": 6, "y": 1}],
                    },
                    {
                        "name": "salvage",
                        "positions": [{"x": 5, "y": 7}, {"x": 6, "y": 0}],
                    },
                    {
                        "name": "exit",
                        "positions": [{"x": 7, "y": 7}],
                    },
                ],
                "actors": [
                    {
                        "id": "player",
                        "kind": "player",
                        "position": {"x": 1, "y": 1},
                    },
                    {
                        "id": "drone-1",
                        "kind": "drone",
                        "position": {"x": 3, "y": 3},
                    },
                    {
                        "id": "drone-2",
                        "kind": "drone",
                        "position": {"x": 2, "y": 0},
                    },
                ],
                "messages": [
                    "Scanners sweep the corridor.",
                    "Drone motors spike nearby.",
                ],
                "hud": {
                    "energy": 9,
                    "hull": {"current": 2, "max": 4},
                    "level_name": "Abandoned Dock",
                    "salvage_progress": {
                        "collected": 2,
                        "remaining_on_map": 2,
                        "remaining_to_goal": 1,
                        "required": 3,
                    },
                    "score": 275,
                    "turn": 5,
                },
                "status": "playing",
                "terminal": False,
                "annotations": [
                    {
                        "position": {"x": 1, "y": 1},
                        "actor_tags": ["player"],
                        "overlay_flags": ["point_of_interest", "under_threat"],
                        "values": {
                            "player": {
                                "drones_in_chase_range": 2,
                                "exit_distance": 12,
                                "nearest_drone": {
                                    "distance": 2,
                                    "id": "drone-2",
                                    "in_chase_range": True,
                                    "position": {"x": 2, "y": 0},
                                },
                                "nearest_salvage": {
                                    "distance": 6,
                                    "position": {"x": 6, "y": 0},
                                },
                                "remaining_to_goal": 1,
                                "salvage_goal_met": False,
                            }
                        },
                    },
                    {
                        "position": {"x": 2, "y": 0},
                        "actor_tags": ["drone"],
                        "overlay_flags": [
                            "chase_range",
                            "nearest_drone",
                            "point_of_interest",
                            "threat",
                        ],
                        "values": {
                            "drone": {
                                "chase_distance": 4,
                                "distance_to_player": 2,
                                "id": "drone-2",
                                "in_chase_range": True,
                                "patrol_anchor": {"x": 3, "y": 7},
                            }
                        },
                    },
                    {
                        "position": {"x": 3, "y": 3},
                        "actor_tags": ["drone"],
                        "overlay_flags": [
                            "chase_range",
                            "point_of_interest",
                            "threat",
                        ],
                        "values": {
                            "drone": {
                                "chase_distance": 4,
                                "distance_to_player": 4,
                                "id": "drone-1",
                                "in_chase_range": True,
                                "patrol_anchor": {"x": 7, "y": 3},
                            }
                        },
                    },
                    {
                        "position": {"x": 5, "y": 5},
                        "terrain_tags": ["hazard"],
                        "overlay_flags": ["danger", "point_of_interest"],
                        "values": {
                            "hazard": {
                                "damage": 1,
                                "distance_to_player": 8,
                            }
                        },
                    },
                    {
                        "position": {"x": 5, "y": 7},
                        "terrain_tags": ["salvage"],
                        "overlay_flags": ["objective", "point_of_interest"],
                        "values": {
                            "salvage": {
                                "distance_to_player": 10,
                                "needed_for_goal": True,
                            }
                        },
                    },
                    {
                        "position": {"x": 6, "y": 0},
                        "terrain_tags": ["salvage"],
                        "overlay_flags": [
                            "nearest_salvage",
                            "objective",
                            "point_of_interest",
                        ],
                        "values": {
                            "salvage": {
                                "distance_to_player": 6,
                                "needed_for_goal": True,
                            }
                        },
                    },
                    {
                        "position": {"x": 6, "y": 1},
                        "terrain_tags": ["hazard"],
                        "overlay_flags": ["danger", "point_of_interest"],
                        "values": {
                            "hazard": {
                                "damage": 1,
                                "distance_to_player": 5,
                            }
                        },
                    },
                    {
                        "position": {"x": 7, "y": 7},
                        "terrain_tags": ["exit"],
                        "overlay_flags": [
                            "extract_locked",
                            "objective",
                            "point_of_interest",
                        ],
                        "values": {
                            "exit": {
                                "distance_to_player": 12,
                                "ready_for_extraction": False,
                                "remaining_to_goal": 1,
                            }
                        },
                    },
                ],
            },
        )

    def test_same_seed_and_commands_produce_same_snapshot_sequence(self) -> None:
        commands = ["scan", "s", "d", "wait", "dash d"]

        def build_sequence() -> list[dict[str, object]]:
            state = GameState.new(build_level(seed=0), energy=12, hull=3)
            state.push_message("Welcome to Salvage Run.")
            sequence = [snapshot_state(state).to_dict()]

            for command in commands:
                apply_command(state, command)
                sequence.append(snapshot_state(state).to_dict())

            return sequence

        first = build_sequence()
        second = build_sequence()

        self.assertEqual(first, second)
        self.assertIsInstance(json.dumps(first), str)

    def test_engine_replay_matches_manual_snapshot_progression(self) -> None:
        commands = ["scan", "s", "d", "wait", "dash d", "quit"]

        replay_state = GameState.new(build_level(seed=0), energy=12, hull=3)
        replay_state.push_message("Welcome to Salvage Run.")
        replay_state.push_message(HELP_TEXT)
        replay = run_command_replay(replay_state, commands, apply_command, snapshot_state)

        manual_state = GameState.new(build_level(seed=0), energy=12, hull=3)
        manual_state.push_message("Welcome to Salvage Run.")
        manual_state.push_message(HELP_TEXT)
        manual_initial = snapshot_state(manual_state).to_dict()
        manual_steps: list[tuple[str, dict[str, object]]] = []

        for command in commands:
            if manual_state.status != "playing":
                break
            apply_command(manual_state, command)
            manual_steps.append((command, snapshot_state(manual_state).to_dict()))

        self.assertEqual(replay.initial_snapshot.to_dict(), manual_initial)
        self.assertEqual(replay.final_snapshot.to_dict(), snapshot_state(manual_state).to_dict())
        self.assertEqual(replay.terminal_status, manual_state.status)
        self.assertEqual(
            [step.raw_command for step in replay.steps],
            [command for command, _ in manual_steps],
        )
        self.assertEqual(replay.steps[0].snapshot.to_dict(), manual_steps[0][1])
        self.assertEqual(replay.steps[2].snapshot.to_dict(), manual_steps[2][1])
        self.assertEqual(replay.steps[-1].snapshot.to_dict(), manual_steps[-1][1])

    def test_script_mode_replays_commands_from_file(self) -> None:
        script_path = TEST_FIXTURES / "script_quick_run.txt"
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli.main(["--script", str(script_path)])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Command> scan", rendered)
        self.assertIn("Command> quit", rendered)
        self.assertIn("Run aborted.", rendered)
        self.assertNotIn("Command> # quick run", rendered)

    def test_script_mode_reads_from_standard_input(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), patch("sys.stdin", io.StringIO("quit\n")):
            result = cli.main(["--script", "-"])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Command> quit", rendered)
        self.assertIn("Run aborted.", rendered)

    def test_script_mode_reports_unfinished_runs(self) -> None:
        script_path = TEST_FIXTURES / "script_partial.txt"
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli.main(["--script", str(script_path)])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Command script ended before the run was resolved.", rendered)

    def test_quiet_script_mode_suppresses_per_turn_output(self) -> None:
        script_path = TEST_FIXTURES / "script_quiet.txt"
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli.main(["--script", str(script_path), "--quiet-script"])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertNotIn("Command> scan", rendered)
        self.assertNotIn("Command> quit", rendered)
        self.assertEqual(rendered.count("Map: "), 1)
        self.assertIn("Run aborted.", rendered)

    def test_quiet_script_requires_script_mode(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            cli.parse_args(["--quiet-script"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("--quiet-script requires --script", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
