from __future__ import annotations

from collections.abc import Callable

from .grid import Position


def render_rect_grid(
    width: int,
    height: int,
    tile_for: Callable[[Position], str],
    *,
    separator: str = " ",
) -> str:
    rows: list[str] = []

    for y in range(height):
        cells: list[str] = []
        for x in range(width):
            cells.append(tile_for(Position(x, y)))
        rows.append(separator.join(cells))

    return "\n".join(rows)
