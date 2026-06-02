from __future__ import annotations

from dataclasses import dataclass, field

from game_engine import Position, RectGrid, push_capped_message

@dataclass(frozen=True)
class Level(RectGrid):
    player_start: Position
    exit_position: Position
    hazards: frozenset[Position]
    salvage: frozenset[Position]
    drone_starts: tuple[Position, ...]
    required_salvage: int


@dataclass
class GameState:
    level: Level
    player: Position
    drones: list[Position]
    salvage_remaining: set[Position]
    energy: int = 18
    hull: int = 3
    max_hull: int = 3
    salvage_collected: int = 0
    turn: int = 0
    status: str = "playing"
    messages: list[str] = field(default_factory=list)

    @classmethod
    def new(cls, level: Level, energy: int = 18, hull: int = 3, max_hull: int | None = None) -> "GameState":
        resolved_max_hull = hull if max_hull is None else max_hull
        return cls(
            level=level,
            player=level.player_start,
            drones=list(level.drone_starts),
            salvage_remaining=set(level.salvage),
            energy=energy,
            hull=hull,
            max_hull=resolved_max_hull,
        )

    def push_message(self, message: str) -> None:
        push_capped_message(self.messages, message, limit=6)

    @property
    def salvage_goal_met(self) -> bool:
        return self.salvage_collected >= self.level.required_salvage

    @property
    def remaining_to_goal(self) -> int:
        return max(0, self.level.required_salvage - self.salvage_collected)

    @property
    def score(self) -> int:
        return (self.salvage_collected * 100) + (self.energy * 5) + (self.hull * 20) - (self.turn * 2)
