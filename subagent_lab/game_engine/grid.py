from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Position:
    x: int
    y: int

    def moved(self, dx: int, dy: int) -> "Position":
        return Position(self.x + dx, self.y + dy)

    def manhattan(self, other: "Position") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


@dataclass(frozen=True)
class RectGrid:
    name: str
    width: int
    height: int
    walls: frozenset[Position]

    def in_bounds(self, position: Position) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height
