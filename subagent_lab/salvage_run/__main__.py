from __future__ import annotations

import argparse
import sys
from typing import Iterable, Sequence, TextIO

from game_engine import run_command_replay

from .engine import HELP_TEXT, apply_command
from .levels import build_level
from .models import GameState
from .snapshot import snapshot_state
from .ui import DEFAULT_THEME, SUPPORTED_THEMES, render_game


def _configure_output_encoding(theme: str) -> None:
    if theme == DEFAULT_THEME:
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except ValueError:
                pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play Salvage Run in the console.")
    parser.add_argument("--seed", type=int, default=0, help="Choose a deterministic map variant.")
    parser.add_argument("--energy", type=int, default=18, help="Starting energy.")
    parser.add_argument("--hull", type=int, default=3, help="Starting hull points.")
    parser.add_argument(
        "--script",
        help="Replay commands from a text file. Use - to read commands from standard input.",
    )
    parser.add_argument(
        "--quiet-script",
        action="store_true",
        help="Only with --script: suppress per-turn snapshots and echoed commands.",
    )
    parser.add_argument(
        "--theme",
        choices=SUPPORTED_THEMES,
        default=DEFAULT_THEME,
        help="Choose the render theme.",
    )
    args = parser.parse_args(argv)
    if args.quiet_script and not args.script:
        parser.error("--quiet-script requires --script")
    return args


def iter_script_commands(script_path: str, stdin: TextIO | None = None) -> Iterable[str]:
    if script_path == "-":
        yield from _iter_commands(stdin or sys.stdin)
        return

    with open(script_path, encoding="utf-8") as handle:
        yield from _iter_commands(handle)


def _iter_commands(stream: TextIO) -> Iterable[str]:
    for raw_line in stream:
        command = raw_line.strip()
        if not command or command.startswith("#"):
            continue
        yield command


def _print_state(state: GameState, *, theme: str = DEFAULT_THEME) -> None:
    print()
    print(render_game(state, theme=theme))


def _finish_run(state: GameState, *, theme: str = DEFAULT_THEME) -> int:
    _print_state(state, theme=theme)
    if state.status == "won":
        print("\nExtraction complete. You win.")
        return 0
    if state.status == "quit":
        print("\nRun aborted.")
        return 0
    if state.status == "playing":
        print("\nCommand script ended before the run was resolved.")
        return 0

    print("\nRun failed.")
    return 1


def _run_scripted(
    state: GameState,
    commands: Iterable[str],
    *,
    quiet: bool = False,
    theme: str = DEFAULT_THEME,
) -> int:
    rendered_turns: list[str] = []

    def apply_script_command(current_state: GameState, command: str) -> None:
        if not quiet:
            rendered_turns.append(render_game(current_state, theme=theme))
        apply_command(current_state, command)

    replay = run_command_replay(
        state,
        commands,
        apply_script_command,
        snapshot_state,
    )

    if not quiet:
        for rendered_state, step in zip(rendered_turns, replay.steps):
            print()
            print(rendered_state)
            print(f"\nCommand> {step.raw_command}")

    return _finish_run(state, theme=theme)


def _run_interactive(state: GameState, *, theme: str = DEFAULT_THEME) -> int:
    while state.status == "playing":
        _print_state(state, theme=theme)
        try:
            command = input("\nCommand> ")
        except EOFError:
            state.status = "quit"
            state.push_message("Input stream ended. Aborting the run.")
            break
        apply_command(state, command)

    return _finish_run(state, theme=theme)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    _configure_output_encoding(args.theme)
    level = build_level(seed=args.seed)
    state = GameState.new(level, energy=args.energy, hull=args.hull)
    state.push_message("Welcome to Salvage Run.")
    state.push_message(HELP_TEXT)

    if args.script:
        return _run_scripted(
            state,
            iter_script_commands(args.script),
            quiet=args.quiet_script,
            theme=args.theme,
        )

    return _run_interactive(state, theme=args.theme)


if __name__ == "__main__":
    raise SystemExit(main())
