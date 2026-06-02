from __future__ import annotations

from collections.abc import Sequence

from game_engine import (
    CARDINAL_DELTAS,
    CommandArgumentSpec,
    CommandSpec,
    export_command_manifest,
    normalize_command_token,
    parse_command as parse_manifest_command,
)


_DIRECTION_ARG = CommandArgumentSpec(
    name="dir",
    choices=tuple(CARDINAL_DELTAS),
    hint="w|a|s|d",
)


COMMAND_SPECS = (
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
        command_id="move_west",
        primary_token="a",
        label="Move Left",
        description="move",
        aliases=("left",),
        hotkeys=("A", "Left"),
        category="movement",
    ),
    CommandSpec(
        command_id="move_south",
        primary_token="s",
        label="Move Down",
        description="move",
        aliases=("down",),
        hotkeys=("S", "Down"),
        category="movement",
    ),
    CommandSpec(
        command_id="move_east",
        primary_token="d",
        label="Move Right",
        description="move",
        aliases=("right",),
        hotkeys=("D", "Right"),
        category="movement",
    ),
    CommandSpec(
        command_id="scan",
        primary_token="scan",
        label="Scan Area",
        description="reports the nearest salvage, the nearest drone, and how many drones can chase you",
        hotkeys=("scan",),
    ),
    CommandSpec(
        command_id="dash",
        primary_token="dash",
        label="Dash",
        description="lunges two tiles for extra energy but can smash your hull",
        args=(_DIRECTION_ARG,),
    ),
    CommandSpec(
        command_id="repair",
        primary_token="repair",
        label="Repair Hull",
        description="spends energy to restore hull",
        aliases=("r",),
        hotkeys=("R",),
    ),
    CommandSpec(
        command_id="wait",
        primary_token="wait",
        label="Hold Position",
        description="skips a turn",
        aliases=(".",),
        hotkeys=(".",),
    ),
    CommandSpec(
        command_id="help",
        primary_token="help",
        label="Help",
        description="repeats this text",
        aliases=("h", "?"),
        hotkeys=("H", "?"),
    ),
    CommandSpec(
        command_id="quit",
        primary_token="quit",
        label="Quit",
        description="exits the run",
        hotkeys=("Q",),
    ),
)


COMMAND_MANIFEST = tuple(export_command_manifest(COMMAND_SPECS))


def normalize_command(raw: str) -> str:
    return normalize_command_token(raw, COMMAND_SPECS)


def parse_command(raw: str) -> tuple[str, list[str]]:
    return parse_manifest_command(raw, COMMAND_SPECS)


def build_help_text(specs: Sequence[CommandSpec] = COMMAND_SPECS) -> str:
    fragments: list[str] = []
    movement_commands = tuple(spec for spec in specs if spec.category == "movement")
    if movement_commands:
        fragments.append(f"{'/'.join(spec.primary_token for spec in movement_commands)} move")

    for spec in specs:
        if spec.category == "movement":
            continue
        fragments.append(f"{spec.usage} {spec.description}")

    return f"Commands: {', '.join(fragments)}."


HELP_TEXT = build_help_text()
