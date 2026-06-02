from __future__ import annotations

from game_engine import Position

from .models import Level


LEVEL_TEMPLATES = [
    (
        "Abandoned Dock",
        3,
        [
            "@..#..$.",
            "..#...!.",
            ".$..#...",
            "....#..D",
            ".##.....",
            "..$..!.#",
            ".#...#..",
            "...D..$E",
        ],
    ),
    (
        "Signal Maze",
        3,
        [
            "@....#..",
            ".##.$..!",
            "...#....",
            ".D...##.",
            "..$.....",
            "#..!.#..",
            "..##..$.",
            "...D...E",
        ],
    ),
    (
        "Frozen Relay",
        4,
        [
            "@.#...$.",
            "..#..!..",
            ".$...#..",
            ".###...D",
            "....$...",
            "..!#..#.",
            ".D..#..$",
            ".......E",
        ],
    ),
]


def build_level(seed: int = 0) -> Level:
    name, required_salvage, rows = LEVEL_TEMPLATES[seed % len(LEVEL_TEMPLATES)]
    width = len(rows[0])
    height = len(rows)
    walls: set[Position] = set()
    hazards: set[Position] = set()
    salvage: set[Position] = set()
    drones: list[Position] = []
    player_start: Position | None = None
    exit_position: Position | None = None

    for y, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"Level {name!r} has inconsistent row widths.")
        for x, cell in enumerate(row):
            position = Position(x, y)
            if cell == "#":
                walls.add(position)
            elif cell == "!":
                hazards.add(position)
            elif cell == "$":
                salvage.add(position)
            elif cell == "D":
                drones.append(position)
            elif cell == "@":
                player_start = position
            elif cell == "E":
                exit_position = position
            elif cell != ".":
                raise ValueError(f"Unsupported level tile {cell!r} in {name!r}.")

    if player_start is None or exit_position is None:
        raise ValueError(f"Level {name!r} is missing a player start or exit.")

    return Level(
        name=name,
        width=width,
        height=height,
        player_start=player_start,
        exit_position=exit_position,
        walls=frozenset(walls),
        hazards=frozenset(hazards),
        salvage=frozenset(salvage),
        drone_starts=tuple(drones),
        required_salvage=required_salvage,
    )
