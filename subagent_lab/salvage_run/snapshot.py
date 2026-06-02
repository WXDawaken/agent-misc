from __future__ import annotations

from dataclasses import dataclass, field

from game_engine import Position, Snapshot, SnapshotActor, SnapshotAnnotation, SnapshotLayer, SnapshotSize

from .engine import DRONE_CHASE_DISTANCE
from .models import GameState


def snapshot_state(state: GameState) -> Snapshot:
    return Snapshot(
        board=SnapshotSize.from_grid(state.level),
        layers=(
            SnapshotLayer.from_positions("walls", state.level.walls),
            SnapshotLayer.from_positions("hazards", state.level.hazards),
            SnapshotLayer.from_positions("salvage", state.salvage_remaining),
            SnapshotLayer.from_positions("exit", [state.level.exit_position]),
        ),
        actors=(
            SnapshotActor.from_position("player", "player", state.player),
            *(
                SnapshotActor.from_position(f"drone-{index}", "drone", drone)
                for index, drone in enumerate(state.drones, start=1)
            ),
        ),
        messages=tuple(state.messages),
        hud={
            "energy": state.energy,
            "hull": {"current": state.hull, "max": state.max_hull},
            "level_name": state.level.name,
            "salvage_progress": {
                "collected": state.salvage_collected,
                "required": state.level.required_salvage,
                "remaining_on_map": len(state.salvage_remaining),
                "remaining_to_goal": state.remaining_to_goal,
            },
            "score": state.score,
            "turn": state.turn,
        },
        status=state.status,
        terminal=state.status != "playing",
        annotations=_build_annotations(state),
    )


@dataclass
class _AnnotationParts:
    terrain_tags: set[str] = field(default_factory=set)
    actor_tags: set[str] = field(default_factory=set)
    overlay_flags: set[str] = field(default_factory=set)
    values: dict[str, object] = field(default_factory=dict)


def _build_annotations(state: GameState) -> tuple[SnapshotAnnotation, ...]:
    annotations: dict[Position, _AnnotationParts] = {}
    nearest_salvage = _nearest_position(state.player, state.salvage_remaining)
    nearest_drone_index = _nearest_drone_index(state)
    chase_count = sum(
        1 for drone in state.drones if state.player.manhattan(drone) <= DRONE_CHASE_DISTANCE
    )

    for hazard in sorted(state.level.hazards):
        entry = annotations.setdefault(hazard, _AnnotationParts())
        entry.terrain_tags.add("hazard")
        entry.overlay_flags.update(("danger", "point_of_interest"))
        entry.values["hazard"] = {
            "damage": 1,
            "distance_to_player": state.player.manhattan(hazard),
        }

    for salvage in sorted(state.salvage_remaining):
        entry = annotations.setdefault(salvage, _AnnotationParts())
        entry.terrain_tags.add("salvage")
        entry.overlay_flags.update(("objective", "point_of_interest"))
        if salvage == nearest_salvage:
            entry.overlay_flags.add("nearest_salvage")
        entry.values["salvage"] = {
            "distance_to_player": state.player.manhattan(salvage),
            "needed_for_goal": state.remaining_to_goal > 0,
        }

    exit_entry = annotations.setdefault(state.level.exit_position, _AnnotationParts())
    exit_entry.terrain_tags.add("exit")
    exit_entry.overlay_flags.update(("objective", "point_of_interest"))
    exit_entry.overlay_flags.add("extract_ready" if state.salvage_goal_met else "extract_locked")
    exit_entry.values["exit"] = {
        "distance_to_player": state.player.manhattan(state.level.exit_position),
        "ready_for_extraction": state.salvage_goal_met,
        "remaining_to_goal": state.remaining_to_goal,
    }

    player_entry = annotations.setdefault(state.player, _AnnotationParts())
    player_entry.actor_tags.add("player")
    player_entry.overlay_flags.add("point_of_interest")
    if chase_count:
        player_entry.overlay_flags.add("under_threat")
    player_entry.values["player"] = {
        "drones_in_chase_range": chase_count,
        "exit_distance": state.player.manhattan(state.level.exit_position),
        "nearest_drone": _nearest_drone_payload(state, nearest_drone_index),
        "nearest_salvage": _nearest_position_payload(state.player, nearest_salvage),
        "remaining_to_goal": state.remaining_to_goal,
        "salvage_goal_met": state.salvage_goal_met,
    }

    for index, drone in enumerate(state.drones, start=1):
        entry = annotations.setdefault(drone, _AnnotationParts())
        entry.actor_tags.add("drone")
        entry.overlay_flags.update(("point_of_interest", "threat"))
        distance = state.player.manhattan(drone)
        in_chase_range = distance <= DRONE_CHASE_DISTANCE
        if in_chase_range:
            entry.overlay_flags.add("chase_range")
        if index - 1 == nearest_drone_index:
            entry.overlay_flags.add("nearest_drone")
        anchor = drone
        if index - 1 < len(state.level.drone_starts):
            anchor = state.level.drone_starts[index - 1]
        entry.values["drone"] = {
            "chase_distance": DRONE_CHASE_DISTANCE,
            "distance_to_player": distance,
            "id": f"drone-{index}",
            "in_chase_range": in_chase_range,
            "patrol_anchor": _position_payload(anchor),
        }

    return tuple(
        SnapshotAnnotation.from_position(
            position,
            terrain_tags=parts.terrain_tags,
            actor_tags=parts.actor_tags,
            overlay_flags=parts.overlay_flags,
            values=parts.values,
        )
        for position, parts in annotations.items()
    )


def _nearest_drone_index(state: GameState) -> int | None:
    if not state.drones:
        return None
    return min(
        range(len(state.drones)),
        key=lambda index: (
            state.player.manhattan(state.drones[index]),
            state.drones[index].y,
            state.drones[index].x,
            index,
        ),
    )


def _nearest_drone_payload(state: GameState, nearest_drone_index: int | None) -> dict[str, object] | None:
    if nearest_drone_index is None:
        return None
    drone = state.drones[nearest_drone_index]
    distance = state.player.manhattan(drone)
    return {
        "distance": distance,
        "id": f"drone-{nearest_drone_index + 1}",
        "in_chase_range": distance <= DRONE_CHASE_DISTANCE,
        "position": _position_payload(drone),
    }


def _nearest_position(
    origin: Position,
    positions: set[Position],
) -> Position | None:
    if not positions:
        return None
    return min(positions, key=lambda position: (origin.manhattan(position), position.y, position.x))


def _nearest_position_payload(origin: Position, position: Position | None) -> dict[str, object] | None:
    if position is None:
        return None
    return {
        "distance": origin.manhattan(position),
        "position": _position_payload(position),
    }


def _position_payload(position: Position) -> dict[str, int]:
    return {"x": position.x, "y": position.y}
