from __future__ import annotations

from game_engine import CARDINAL_DELTAS

from .commands import HELP_TEXT, normalize_command, parse_command
from .models import GameState, Position


DIRECTION_DELTAS = CARDINAL_DELTAS
DRONE_CHASE_DISTANCE = 4


def apply_command(state: GameState, raw_command: str) -> GameState:
    if state.status != "playing":
        state.push_message("The run is already over. Start a new game to play again.")
        return state

    command, args = parse_command(raw_command)

    if args and command != "dash":
        state.push_message(f"Unknown command: {raw_command!r}. Type help for controls.")
        return state

    if command == "help":
        state.push_message(HELP_TEXT)
        return state
    if command == "quit":
        state.status = "quit"
        state.push_message("You abandon the run and power down the rig.")
        return state
    if command == "scan":
        _consume_turn(state)
        _scan_area(state)
        _finalize_turn(state)
        return state
    if command == "dash":
        if len(args) != 1 or args[0] not in DIRECTION_DELTAS:
            state.push_message("Usage: dash <w|a|s|d>.")
            return state
        if state.energy < 3:
            state.push_message("You need at least 3 energy to commit to a dash.")
            return state

        _consume_turn(state)
        state.energy -= 2
        _dash_player(state, args[0])
        _finalize_turn(state)
        return state
    if command == "repair":
        if state.hull >= state.max_hull:
            state.push_message("Hull is already fully patched.")
            return state
        if state.energy < 3:
            state.push_message("You need at least 3 energy to run a field repair.")
            return state

        _consume_turn(state)
        state.energy -= 2
        state.hull = min(state.max_hull, state.hull + 1)
        state.push_message("You weld on a quick patch and restore 1 hull.")
        _finalize_turn(state)
        return state
    if command == "wait":
        _consume_turn(state)
        state.push_message("You hold position and listen for drone motors.")
        _finalize_turn(state)
        return state
    if command in DIRECTION_DELTAS:
        dx, dy = DIRECTION_DELTAS[command]
        candidate = state.player.moved(dx, dy)
        if not state.level.in_bounds(candidate):
            state.push_message("The bulkhead blocks that direction.")
            return state
        if candidate in state.level.walls:
            state.push_message("You bump into scrap plating and lose no time.")
            return state

        state.player = candidate
        _consume_turn(state)
        _resolve_player_tile(state)
        _finalize_turn(state)
        return state

    state.push_message(f"Unknown command: {raw_command!r}. Type help for controls.")
    return state


def _consume_turn(state: GameState) -> None:
    state.turn += 1
    state.energy -= 1


def _resolve_player_tile(state: GameState) -> None:
    if state.player in state.salvage_remaining:
        state.salvage_remaining.remove(state.player)
        state.salvage_collected += 1
        state.push_message("You secure a salvage crate.")

    if state.player in state.level.hazards:
        state.hull -= 1
        state.push_message("Static arcs through the deck. Hull takes 1 damage.")

    if state.player == state.level.exit_position:
        if state.salvage_goal_met:
            state.status = "won"
            state.push_message("You reach the shuttle with enough salvage to call it a win.")
        else:
            state.push_message(
                f"The shuttle refuses to launch. You still need {state.remaining_to_goal} salvage."
            )


def _dash_player(state: GameState, direction: str) -> None:
    dx, dy = DIRECTION_DELTAS[direction]

    for _ in range(2):
        candidate = state.player.moved(dx, dy)
        if not state.level.in_bounds(candidate):
            state.hull -= 1
            state.push_message("You misjudge the lane and slam into a bulkhead. Hull takes 1 damage.")
            return
        if candidate in state.level.walls:
            state.hull -= 1
            state.push_message("You smash into scrap plating mid-dash. Hull takes 1 damage.")
            return

        state.player = candidate
        _resolve_player_tile(state)
        if state.status != "playing" or state.hull <= 0:
            return


def _scan_area(state: GameState) -> None:
    salvage_message = "All required salvage is already secured."
    if state.salvage_remaining:
        target = min(state.salvage_remaining, key=lambda pos: state.player.manhattan(pos))
        salvage_message = (
            f"Nearest salvage is {state.player.manhattan(target)} steps away at "
            f"({target.x}, {target.y})."
        )

    drone_message = "No drones are active on this map."
    if state.drones:
        drone = min(state.drones, key=lambda pos: state.player.manhattan(pos))
        drone_distance = state.player.manhattan(drone)
        chase_status = (
            "It's close enough to start chasing you."
            if drone_distance <= DRONE_CHASE_DISTANCE
            else "It's still too far away to start chasing you."
        )
        drone_message = (
            f"Nearest drone is {drone_distance} steps away at ({drone.x}, {drone.y}). "
            f"{chase_status}"
        )

    chase_count = sum(
        1 for drone in state.drones if state.player.manhattan(drone) <= DRONE_CHASE_DISTANCE
    )
    chase_message = (
        "1 drone is currently in chase range."
        if chase_count == 1
        else f"{chase_count} drones are currently in chase range."
    )

    exit_distance = state.player.manhattan(state.level.exit_position)
    state.push_message(salvage_message)
    state.push_message(drone_message)
    state.push_message(chase_message)
    state.push_message(f"Extraction shuttle is {exit_distance} steps away.")


def _finalize_turn(state: GameState) -> None:
    if state.status != "playing":
        return
    if state.energy <= 0:
        state.status = "lost"
        state.push_message("Your battery pack dies in the dark.")
        return
    if state.hull <= 0:
        state.status = "lost"
        state.push_message("The salvage rig breaks apart before extraction.")
        return

    _move_drones(state)

    if state.status != "playing":
        return
    if state.energy <= 0:
        state.status = "lost"
        state.push_message("Your battery pack dies in the dark.")
    elif state.hull <= 0:
        state.status = "lost"
        state.push_message("The salvage rig breaks apart before extraction.")


def _move_drones(state: GameState) -> None:
    occupied = set()
    new_positions: list[Position] = []
    player_hit = 0

    for index, drone in enumerate(state.drones):
        anchor = drone
        if index < len(state.level.drone_starts):
            anchor = state.level.drone_starts[index]
        next_position = _choose_drone_step(
            state=state,
            drone=drone,
            anchor=anchor,
            blocked=occupied,
        )
        if next_position == state.player:
            player_hit += 1
            occupied.add(drone)
            new_positions.append(drone)
        else:
            occupied.add(next_position)
            new_positions.append(next_position)

    state.drones = new_positions

    if player_hit:
        state.hull -= player_hit
        state.push_message(f"Drone contact. Hull takes {player_hit} damage.")


def _choose_drone_step(
    state: GameState,
    drone: Position,
    anchor: Position,
    blocked: set[Position],
) -> Position:
    candidates = [drone]
    for dx, dy in DIRECTION_DELTAS.values():
        candidate = drone.moved(dx, dy)
        if not state.level.in_bounds(candidate):
            continue
        if candidate in state.level.walls:
            continue
        if candidate in blocked:
            continue
        candidates.append(candidate)

    player_distance = drone.manhattan(state.player)
    if player_distance > DRONE_CHASE_DISTANCE:
        return min(
            candidates,
            key=lambda pos: (
                pos.manhattan(anchor),
                pos.y,
                pos.x,
            ),
        )

    return min(
        candidates,
        key=lambda pos: (
            pos.manhattan(state.player),
            pos.y,
            pos.x,
        ),
    )
