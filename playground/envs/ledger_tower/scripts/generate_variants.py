from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import heapq
import json
import random
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LEDGER_ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND_ROOT = LEDGER_ROOT.parents[1]
if str(LEDGER_ROOT) not in sys.path:
    sys.path.insert(0, str(LEDGER_ROOT))

import game as ledger_game  # noqa: E402


GENERATOR_ID = "graph_grammar_solver_v1"
DEFAULT_BASE_DATA = LEDGER_ROOT / "data" / "ledger_tower_boss_gated.json"
DEFAULT_GOAL = {
    "victory": True,
    "item": "ledger_core",
    "hp_min": 40,
    "route_score_min": 14000,
}

FLOOR_NAMES = [
    "Entry Ledger",
    "Key Annex",
    "Trade Mezzanine",
    "Guard Accounts",
    "Vault Balance",
    "Final Audit",
]

BOSS_ENEMIES = [
    "entry_auditor",
    "annex_auditor",
    "trade_auditor",
    "guard_auditor",
    "vault_auditor",
    "balance_auditor",
]

MANDATORY_ITEMS = {
    1: [("attack", "attack_gem", "before"), ("yellow_key", "yellow_key", "before"), ("potion", "small_potion", "after")],
    2: [("defense", "defense_gem", "before"), ("attack", "attack_gem", "after"), ("potion", "big_potion", "after")],
    3: [("yellow_key", "yellow_key", "before"), ("potion", "small_potion", "after"), ("defense", "defense_gem", "after")],
    4: [("attack", "attack_gem", "before"), ("defense", "defense_gem", "before"), ("potion", "big_potion", "before")],
    5: [("potion_small", "small_potion", "before"), ("attack", "attack_gem", "before"), ("yellow_key", "yellow_key", "after"), ("potion_big", "big_potion", "after")],
    6: [("defense", "defense_gem", "before"), ("attack", "attack_gem", "before")],
}

PROFILE_DESCRIPTIONS = {
    "branchy_score": "Adds optional score branches around a boss-bearing spine.",
    "shop_timing": "Moves shop pressure earlier and adds gold enemies before purchase decisions.",
    "key_pressure": "Adds carried-key gates plus optional blue-door reward branches.",
}

PRIMARY_PLACEMENT_MIN_DISTANCE = 3
STRUCTURAL_PLACEMENT_MIN_DISTANCE = 2


def floor_stage(floor_index: int, floor_count: int) -> int:
    if floor_count < 2:
        raise ValueError("floor_count must be at least 2")
    stage_span = len(FLOOR_NAMES) - 1
    floor_span = floor_count - 1
    return 1 + ((floor_index - 1) * stage_span + floor_span // 2) // floor_span


def generated_floor_name(floor_index: int, floor_count: int, stage: int) -> str:
    if floor_count == len(FLOOR_NAMES):
        return FLOOR_NAMES[floor_index - 1]
    if floor_index == floor_count:
        return FLOOR_NAMES[-1]
    return f"{FLOOR_NAMES[stage - 1]} {floor_index:02d}"


@dataclass(frozen=True)
class RouteResult:
    reward: int
    route_score: int
    moves: int
    hp: int
    atk: int
    defense: int
    gold: int
    victory: bool
    goal_achieved: bool | None
    commands: list[str]
    cleared: list[str]


@dataclass
class CandidateRecord:
    profile: str
    seed: str
    index: int
    data: dict[str, Any]
    validation_errors: list[str]
    validation_warnings: list[str]
    solver: dict[str, Any]
    ranking_score: float


def stable_int_seed(seed: str, profile: str, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{profile}:{index}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_grid_size(width: int, height: int) -> tuple[int, int]:
    width = max(9, width)
    height = max(9, height)
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1
    return width, height


def make_blank_grid(width: int, height: int) -> list[list[str]]:
    return [["#" for _ in range(width)] for _ in range(height)]


def in_bounds(grid: list[list[str]], point: tuple[int, int]) -> bool:
    x, y = point
    return 0 <= y < len(grid) and 0 <= x < len(grid[y])


def is_open(grid: list[list[str]], point: tuple[int, int]) -> bool:
    x, y = point
    return in_bounds(grid, point) and grid[y][x] != "#"


def carve(grid: list[list[str]], point: tuple[int, int]) -> None:
    x, y = point
    if in_bounds(grid, point):
        grid[y][x] = "."


def path_between(start: tuple[int, int], end: tuple[int, int], rng: random.Random) -> list[tuple[int, int]]:
    x, y = start
    ex, ey = end
    points = [(x, y)]
    axes = ["x", "y"]
    rng.shuffle(axes)
    for axis in axes:
        if axis == "x":
            while x != ex:
                x += 1 if ex > x else -1
                points.append((x, y))
        else:
            while y != ey:
                y += 1 if ey > y else -1
                points.append((x, y))
    return points


def carve_polyline(
    grid: list[list[str]],
    points: list[tuple[int, int]],
    rng: random.Random,
) -> list[tuple[int, int]]:
    path: list[tuple[int, int]] = []
    for start, end in zip(points, points[1:]):
        segment = path_between(start, end, rng)
        if path:
            segment = segment[1:]
        path.extend(segment)
    for point in path:
        carve(grid, point)
    unique_path: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for point in path:
        if point in seen:
            continue
        unique_path.append(point)
        seen.add(point)
    return unique_path


def adjacent(point: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = point
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def manhattan_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def carve_branch(
    grid: list[list[str]],
    anchor: tuple[int, int],
    length: int,
    rng: random.Random,
) -> list[tuple[int, int]] | None:
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    rng.shuffle(directions)
    for dx, dy in directions:
        x, y = anchor
        cells: list[tuple[int, int]] = []
        ok = True
        previous = anchor
        for _ in range(length):
            x += dx
            y += dy
            point = (x, y)
            if not in_bounds(grid, point):
                ok = False
                break
            if x == 0 or y == 0 or y == len(grid) - 1 or x == len(grid[y]) - 1:
                ok = False
                break
            if grid[y][x] != "#":
                ok = False
                break
            for neighbor in adjacent(point):
                if neighbor == previous:
                    continue
                if neighbor == anchor and not cells:
                    continue
                if is_open(grid, neighbor):
                    ok = False
                    break
            if not ok:
                break
            cells.append(point)
            previous = point
        if ok and cells:
            for point in cells:
                carve(grid, point)
            return cells
    return None


def open_cell_count(grid: list[list[str]]) -> int:
    return sum(1 for row in grid for cell in row if cell != "#")


def grid_open_ratio(grid: list[list[str]]) -> float:
    total = sum(len(row) for row in grid)
    return open_cell_count(grid) / total if total else 0.0


def grid_floor(grid: list[list[str]]) -> dict[str, Any]:
    return {"grid": ["".join(row) for row in grid]}


def preserves_boss_cut(
    grid: list[list[str]],
    *,
    entry: tuple[int, int],
    finish: tuple[int, int],
    gate: tuple[int, int],
) -> bool:
    reachable = static_reachable(grid_floor(grid), [entry], {gate})
    return finish not in reachable


def open_neighbor_count(grid: list[list[str]], point: tuple[int, int]) -> int:
    return sum(1 for neighbor in adjacent(point) if is_open(grid, neighbor))


def interior_wall_cells(grid: list[list[str]]) -> list[tuple[int, int]]:
    return [
        (x, y)
        for y in range(1, len(grid) - 1)
        for x in range(1, len(grid[y]) - 1)
        if grid[y][x] == "#"
    ]


def room_cells_around(
    grid: list[list[str]],
    center: tuple[int, int],
    room_w: int,
    room_h: int,
    rng: random.Random,
) -> list[tuple[int, int]]:
    cx, cy = center
    max_left = max(1, len(grid[0]) - 1 - room_w)
    max_top = max(1, len(grid) - 1 - room_h)
    left = max(1, min(max_left, cx - rng.randrange(room_w)))
    top = max(1, min(max_top, cy - rng.randrange(room_h)))
    return [(x, y) for y in range(top, top + room_h) for x in range(left, left + room_w)]


def carve_roomy_space(
    grid: list[list[str]],
    *,
    entry: tuple[int, int],
    finish: tuple[int, int],
    gate: tuple[int, int],
    path: list[tuple[int, int]],
    room_points: list[tuple[int, int]],
    rng: random.Random,
    target_open_ratio: float,
    boss_gate_mode: str,
    space_style: str,
    loop_budget: int,
) -> dict[str, Any]:
    if space_style not in {"hybrid", "tree", "patch"}:
        raise ValueError(f"unknown space style: {space_style}")

    target_open_ratio = max(0.0, min(0.75, target_open_ratio))
    total = sum(len(row) for row in grid)
    target_open = max(open_cell_count(grid), int(total * target_open_ratio))
    added = 0
    room_cells = 0
    corridor_cells = 0
    filler_cells = 0
    loop_cells = 0
    attempts = 0
    max_attempts = max(200, target_open * 80)

    preserve_cut = boss_gate_mode == "preserve"

    def try_open(cells: list[tuple[int, int]]) -> int:
        nonlocal added
        opened_now: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for x, y in cells:
            if (x, y) in seen:
                continue
            seen.add((x, y))
            if y <= 0 or y >= len(grid) - 1 or x <= 0 or x >= len(grid[y]) - 1:
                continue
            if grid[y][x] != "#":
                continue
            grid[y][x] = "."
            opened_now.append((x, y))
        if not opened_now:
            return 0
        if preserve_cut and not preserves_boss_cut(grid, entry=entry, finish=finish, gate=gate):
            for x, y in opened_now:
                grid[y][x] = "#"
            return 0
        added += len(opened_now)
        return len(opened_now)

    def frontier(max_neighbors: int, *, exact_one: bool = False) -> list[tuple[int, int]]:
        candidates: list[tuple[int, int]] = []
        for point in interior_wall_cells(grid):
            neighbors = open_neighbor_count(grid, point)
            if exact_one and neighbors != 1:
                continue
            if not exact_one and not (1 <= neighbors <= max_neighbors):
                continue
            candidates.append(point)
        return candidates

    if space_style == "hybrid":
        anchors = list(dict.fromkeys([entry, gate, finish, *room_points]))
        rng.shuffle(anchors)
        for point in anchors:
            if open_cell_count(grid) >= target_open:
                break
            if point == gate:
                room_w, room_h = rng.choice([(2, 2), (3, 2), (2, 3)])
            elif point in {entry, finish}:
                room_w, room_h = rng.choice([(2, 2), (3, 2), (2, 3)])
            else:
                room_w, room_h = rng.choice([(2, 2), (2, 3), (3, 2)])
            room_cells += try_open(room_cells_around(grid, point, room_w, room_h, rng))

        widened_path = path[:]
        rng.shuffle(widened_path)
        for point in widened_path:
            if open_cell_count(grid) >= target_open:
                break
            if rng.random() > 0.55:
                continue
            neighbors = adjacent(point)
            rng.shuffle(neighbors)
            for neighbor in neighbors:
                if not in_bounds(grid, neighbor):
                    continue
                nx, ny = neighbor
                if nx <= 0 or ny <= 0 or ny >= len(grid) - 1 or nx >= len(grid[ny]) - 1:
                    continue
                if grid[ny][nx] == "#" and open_neighbor_count(grid, neighbor) <= 2:
                    corridor_cells += try_open([neighbor])
                    break

    while open_cell_count(grid) < target_open and attempts < max_attempts:
        attempts += 1

        if space_style == "patch":
            anchors = [
                (x, y)
                for y in range(1, len(grid) - 1)
                for x in range(1, len(grid[y]) - 1)
                if grid[y][x] != "#"
            ]
            if not anchors:
                break
            anchor = rng.choice(anchors)
            room_w = rng.choice([2, 3, 3, 4])
            room_h = rng.choice([2, 3, 3, 4])
            filler_cells += try_open(room_cells_around(grid, anchor, room_w, room_h, rng))
            continue

        candidates = frontier(2 if space_style == "hybrid" else 1, exact_one=space_style == "tree" or preserve_cut)
        if not candidates:
            break
        if space_style == "hybrid":
            weighted: list[tuple[int, int]] = []
            for point in candidates:
                weight = 3 if open_neighbor_count(grid, point) == 1 else 1
                weighted.extend([point] * weight)
            candidates = weighted
        filler_cells += try_open([rng.choice(candidates)])

    if space_style == "hybrid" and not preserve_cut:
        for _ in range(max(0, loop_budget)):
            candidates = [point for point in interior_wall_cells(grid) if open_neighbor_count(grid, point) >= 2]
            rng.shuffle(candidates)
            for point in candidates:
                opened = try_open([point])
                if opened:
                    loop_cells += opened
                    break

    return {
        "target_open_ratio": round(target_open_ratio, 3),
        "open_cells": open_cell_count(grid),
        "open_ratio": round(grid_open_ratio(grid), 3),
        "added_open_cells": added,
        "room_cells": room_cells,
        "corridor_cells": corridor_cells,
        "filler_cells": filler_cells,
        "loop_cells": loop_cells,
        "attempts": attempts,
        "space_style": space_style,
        "boss_gate_mode": boss_gate_mode,
        "loop_budget": loop_budget,
    }


def path_index(path: list[tuple[int, int]], point: tuple[int, int]) -> int:
    try:
        return path.index(point)
    except ValueError:
        return -1


def choose_path_cell(
    path: list[tuple[int, int]],
    start: int,
    end: int,
    taken: set[tuple[int, int]],
    rng: random.Random,
) -> tuple[int, int]:
    candidates = [point for point in path[start:end] if point not in taken]
    if not candidates:
        candidates = [point for point in path if point not in taken]
    if not candidates:
        raise ValueError("no free path cell available")
    return rng.choice(candidates)


def choose_spread_cell(
    candidates: list[tuple[int, int]],
    *,
    avoid_points: list[tuple[int, int]],
    structural_avoid_points: list[tuple[int, int]] | None = None,
    rng: random.Random,
    preferred_min_distance: int,
    structural_min_distance: int = 0,
    placement_stats: dict[str, Any] | None = None,
) -> tuple[int, int]:
    if not candidates:
        raise ValueError("no free placement cell available")
    structural_avoid_points = structural_avoid_points or []
    if not avoid_points and not structural_avoid_points:
        return rng.choice(candidates)

    def group_score(point: tuple[int, int], points: list[tuple[int, int]]) -> tuple[int, int]:
        if not points:
            return 99, 0
        distances = [manhattan_distance(point, avoid) for avoid in points]
        return min(distances), sum(distances)

    def distance_score(point: tuple[int, int]) -> tuple[int, int, int, int]:
        resource_min, resource_sum = group_score(point, avoid_points)
        structural_min, structural_sum = group_score(point, structural_avoid_points)
        return resource_min, structural_min, resource_sum, structural_sum

    def passes(
        point: tuple[int, int],
        min_distance: int,
        min_structural_distance: int,
    ) -> bool:
        resource_min, structural_min, _resource_sum, _structural_sum = distance_score(point)
        return resource_min >= min_distance and structural_min >= min_structural_distance

    eligible = candidates
    accepted_min_distance = 0
    accepted_structural_min_distance = 0
    found = False
    for min_distance in range(preferred_min_distance, -1, -1):
        for min_structural_distance in range(structural_min_distance, -1, -1):
            spaced = [
                point
                for point in candidates
                if passes(point, min_distance, min_structural_distance)
            ]
            if spaced:
                eligible = spaced
                accepted_min_distance = min_distance
                accepted_structural_min_distance = min_structural_distance
                found = True
                break
        if found:
            break

    if placement_stats is not None:
        placement_stats["choices"] = int(placement_stats.get("choices", 0)) + 1
        if accepted_min_distance < preferred_min_distance:
            placement_stats["relaxed_choices"] = int(placement_stats.get("relaxed_choices", 0)) + 1
        previous = placement_stats.get("lowest_accepted_min_distance")
        if previous is None:
            placement_stats["lowest_accepted_min_distance"] = accepted_min_distance
        else:
            placement_stats["lowest_accepted_min_distance"] = min(int(previous), accepted_min_distance)
        if structural_avoid_points:
            previous_structural = placement_stats.get("lowest_accepted_structural_min_distance")
            if previous_structural is None:
                placement_stats["lowest_accepted_structural_min_distance"] = accepted_structural_min_distance
            else:
                placement_stats["lowest_accepted_structural_min_distance"] = min(
                    int(previous_structural),
                    accepted_structural_min_distance,
                )

    return rng.choice(eligible)


def segment_open_candidates(
    grid: list[list[str]],
    path: list[tuple[int, int]],
    start: int,
    end: int,
    taken: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    start = max(0, start)
    end = min(len(path), end)
    segment_indices = set(range(start, end))
    if not segment_indices:
        return []
    segment_center = (start + end - 1) / 2
    candidates: list[tuple[int, int]] = []
    for y in range(1, len(grid) - 1):
        for x in range(1, len(grid[y]) - 1):
            point = (x, y)
            if point in taken or grid[y][x] == "#":
                continue
            nearest_index = min(
                range(len(path)),
                key=lambda index: (manhattan_distance(point, path[index]), abs(index - segment_center)),
            )
            if nearest_index in segment_indices:
                candidates.append(point)
    return candidates


def choose_placement_cell(
    grid: list[list[str]],
    path: list[tuple[int, int]],
    start: int,
    end: int,
    taken: set[tuple[int, int]],
    rng: random.Random,
    *,
    avoid_points: list[tuple[int, int]],
    structural_avoid_points: list[tuple[int, int]] | None = None,
    placement_stats: dict[str, Any],
    preferred_min_distance: int = PRIMARY_PLACEMENT_MIN_DISTANCE,
    structural_min_distance: int = STRUCTURAL_PLACEMENT_MIN_DISTANCE,
) -> tuple[int, int]:
    candidates = segment_open_candidates(grid, path, start, end, taken)
    if not candidates:
        candidates = [point for point in path[start:end] if point not in taken]
    if not candidates:
        candidates = [point for point in path if point not in taken]
    return choose_spread_cell(
        candidates,
        avoid_points=avoid_points,
        structural_avoid_points=structural_avoid_points,
        rng=rng,
        preferred_min_distance=preferred_min_distance,
        structural_min_distance=structural_min_distance,
        placement_stats=placement_stats,
    )


def collect_resource_points(entities: list[dict[str, Any]]) -> list[tuple[int, int]]:
    return [
        (int(entity["x"]), int(entity["y"]))
        for entity in entities
        if entity["type"] in {"item", "shop"}
    ]


def collect_structural_points(entities: list[dict[str, Any]]) -> list[tuple[int, int]]:
    return [
        (int(entity["x"]), int(entity["y"]))
        for entity in entities
        if entity["type"] in {"stairs", "exit"}
    ]


def add_entity(
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    entity: dict[str, Any],
    point: tuple[int, int],
) -> None:
    if point in taken:
        raise ValueError(f"entity coordinate reused: {point}")
    taken.add(point)
    payload = copy.deepcopy(entity)
    payload["x"], payload["y"] = point
    entities.append(payload)


def add_item(
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    floor_index: int,
    suffix: str,
    item: str,
    point: tuple[int, int],
) -> None:
    add_entity(
        entities,
        taken,
        {"id": f"f{floor_index}_{suffix}", "type": "item", "item": item},
        point,
    )


def add_enemy(
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    floor_index: int,
    suffix: str,
    enemy: str,
    point: tuple[int, int],
) -> None:
    add_entity(
        entities,
        taken,
        {"id": f"f{floor_index}_{suffix}", "type": "enemy", "enemy": enemy},
        point,
    )


def add_shop(
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    floor_index: int,
    suffix: str,
    point: tuple[int, int],
) -> None:
    add_entity(
        entities,
        taken,
        {"id": f"f{floor_index}_{suffix}", "type": "shop", "shop": "standard"},
        point,
    )


def add_door(
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    floor_index: int,
    suffix: str,
    key: str,
    point: tuple[int, int],
) -> None:
    add_entity(
        entities,
        taken,
        {"id": f"f{floor_index}_{suffix}", "type": "door", "key": key},
        point,
    )


def add_optional_branch(
    grid: list[list[str]],
    entities: list[dict[str, Any]],
    taken: set[tuple[int, int]],
    floor_index: int,
    anchor: tuple[int, int],
    specs: list[tuple[str, str, str]],
    rng: random.Random,
    length: int = 3,
) -> bool:
    cells = carve_branch(grid, anchor, length, rng)
    if not cells:
        return False
    if len(specs) == 1:
        placements = [(specs[0], cells[-1])]
    else:
        placements = list(zip(specs, [cells[0], cells[-1]]))
    for (kind, suffix, value), point in placements:
        if kind == "item":
            add_item(entities, taken, floor_index, suffix, value, point)
        elif kind == "enemy":
            add_enemy(entities, taken, floor_index, suffix, value, point)
        elif kind == "door":
            add_door(entities, taken, floor_index, suffix, value, point)
        elif kind == "shop":
            add_shop(entities, taken, floor_index, suffix, point)
        else:
            raise ValueError(f"unknown branch spec kind: {kind}")
    return True


def generate_floor(
    *,
    profile: str,
    floor_index: int,
    floor_count: int,
    stage: int,
    width: int,
    height: int,
    rng: random.Random,
    previous_finish: tuple[int, int] | None,
    next_entry: tuple[int, int],
    open_ratio: float,
    boss_gate_mode: str,
    space_style: str,
    loop_budget: int,
) -> tuple[dict[str, Any], tuple[int, int], list[str]]:
    grid = make_blank_grid(width, height)
    entry = (1, height // 2)
    gate = (max(4, min(width - 4, width // 2 + rng.choice([-1, 0, 1]))), height // 2)
    turn_y = rng.choice([2, 3, max(2, height // 3)])
    turn = (gate[0], turn_y)
    finish_x = max(4, min(width - 3, width // 2 + rng.choice([-1, 0, 1])))
    finish = (finish_x, 1)
    path = carve_polyline(grid, [entry, gate, turn, finish], rng)
    gate_i = path_index(path, gate)
    if gate_i <= 0:
        raise ValueError("generated boss gate is not on the spine")

    entities: list[dict[str, Any]] = []
    taken: set[tuple[int, int]] = set()
    taken.add(finish)
    taken.add(gate)
    boss_motif = "boss_cut" if boss_gate_mode == "preserve" else "boss_spine_node"
    motifs: list[str] = [f"f{floor_index}:stage_{stage}", f"f{floor_index}:{boss_motif}"]

    if previous_finish is not None:
        add_entity(
            entities,
            taken,
            {
                "id": f"f{floor_index}_down",
                "type": "stairs",
                "to_floor": f"f{floor_index - 1}",
                "to_position": list(previous_finish),
            },
            entry,
        )

    before_start = 1
    before_end = gate_i
    after_start = gate_i + 1
    after_end = len(path) - 1

    if profile == "key_pressure" and stage in {2, 4, 6}:
        door_cell = choose_path_cell(path, before_start, before_end, taken, rng)
        add_door(entities, taken, floor_index, "yellow_door", "yellow", door_cell)
        motifs.append(f"f{floor_index}:carried_yellow_gate")

    taken.discard(gate)
    add_enemy(entities, taken, floor_index, "boss", BOSS_ENEMIES[stage - 1], gate)

    if floor_index < floor_count:
        taken.discard(finish)
        add_entity(
            entities,
            taken,
            {
                "id": f"f{floor_index}_up",
                "type": "stairs",
                "to_floor": f"f{floor_index + 1}",
                "to_position": list(next_entry),
            },
            finish,
        )
    else:
        taken.discard(finish)
        add_entity(
            entities,
            taken,
            {"id": f"f{floor_index}_exit", "type": "exit", "requires_item": "ledger_core"},
            finish,
        )

    before_anchors = [point for point in path[before_start:before_end] if point not in taken]
    after_anchors = [point for point in path[after_start:after_end] if point not in taken]
    rng.shuffle(before_anchors)
    rng.shuffle(after_anchors)

    if profile == "branchy_score":
        for anchor in before_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("enemy", "side_wisp", "audit_wisp"), ("item", "side_attack", "attack_gem")],
                rng,
            ):
                motifs.append(f"f{floor_index}:pre_boss_score_branch")
        for anchor in after_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("enemy", "side_sentinel", "coin_sentinel"), ("item", "side_large_potion", "large_potion")],
                rng,
            ):
                motifs.append(f"f{floor_index}:post_boss_score_branch")
    elif profile == "shop_timing":
        for anchor in before_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("enemy", "gold_moth", "ink_moth"), ("item", "gold_potion", "small_potion")],
                rng,
                length=2,
            ):
                motifs.append(f"f{floor_index}:pre_shop_gold_branch")
        for anchor in after_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("enemy", "keeper_branch", "ward_keeper"), ("item", "ward_branch", "ward_gem")],
                rng,
            ):
                motifs.append(f"f{floor_index}:defense_conversion_branch")
    elif profile == "key_pressure":
        for anchor in before_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("enemy", "blue_guard", "brass_guard"), ("item", "blue_key", "blue_key")],
                rng,
            ):
                motifs.append(f"f{floor_index}:optional_blue_key_branch")
        for anchor in after_anchors[:1]:
            if add_optional_branch(
                grid,
                entities,
                taken,
                floor_index,
                anchor,
                [("door", "blue_reward_door", "blue"), ("item", "blue_reward", "sharp_ledger")],
                rng,
                length=2,
            ):
                motifs.append(f"f{floor_index}:optional_blue_reward_branch")
    else:
        raise ValueError(f"unknown profile: {profile}")

    room_points = [entry, gate, finish, *path[:: max(1, len(path) // 4)]]
    for entity in entities:
        entity_type = entity["type"]
        is_structural = entity_type in {"shop", "stairs", "exit"}
        is_core = entity_type == "item" and entity.get("item") == "ledger_core"
        if is_structural or is_core:
            room_points.append((int(entity["x"]), int(entity["y"])))
    space_stats = carve_roomy_space(
        grid,
        entry=entry,
        finish=finish,
        gate=gate,
        path=path,
        room_points=room_points,
        rng=rng,
        target_open_ratio=open_ratio,
        boss_gate_mode=boss_gate_mode,
        space_style=space_style,
        loop_budget=loop_budget,
    )
    space_stats["stage"] = stage
    motifs.append(f"f{floor_index}:{space_style}_space_{space_stats['open_ratio']}")

    placement_stats: dict[str, Any] = {
        "primary_min_distance": PRIMARY_PLACEMENT_MIN_DISTANCE,
        "structural_min_distance": STRUCTURAL_PLACEMENT_MIN_DISTANCE,
        "choices": 0,
        "relaxed_choices": 0,
        "lowest_accepted_min_distance": None,
        "lowest_accepted_structural_min_distance": None,
    }
    resource_points = collect_resource_points(entities)
    structural_points = list(dict.fromkeys([entry, finish, *collect_structural_points(entities)]))

    def placement_avoid_points() -> list[tuple[int, int]]:
        return list(dict.fromkeys([gate, *resource_points]))

    def place_primary_item(suffix: str, item: str, side: str) -> None:
        if side == "before":
            start, end = before_start, before_end
        else:
            start, end = after_start, after_end
        point = choose_placement_cell(
            grid,
            path,
            start,
            end,
            taken,
            rng,
            avoid_points=placement_avoid_points(),
            structural_avoid_points=structural_points,
            placement_stats=placement_stats,
        )
        add_item(entities, taken, floor_index, suffix, item, point)
        resource_points.append(point)

    for suffix, item, side in MANDATORY_ITEMS[stage]:
        place_primary_item(suffix, item, side)

    if stage >= 3:
        shop_side = "before" if profile == "shop_timing" and stage in {4, 6} else "after"
        if shop_side == "before":
            start, end = before_start, before_end
        else:
            start, end = after_start, after_end
        point = choose_placement_cell(
            grid,
            path,
            start,
            end,
            taken,
            rng,
            avoid_points=placement_avoid_points(),
            structural_avoid_points=structural_points,
            placement_stats=placement_stats,
        )
        add_shop(entities, taken, floor_index, "shop", point)
        resource_points.append(point)
        motifs.append(f"f{floor_index}:shop_{shop_side}_boss")

    if floor_index == floor_count:
        core_cell = choose_placement_cell(
            grid,
            path,
            after_start,
            after_end,
            taken,
            rng,
            avoid_points=placement_avoid_points(),
            structural_avoid_points=structural_points,
            placement_stats=placement_stats,
        )
        add_item(entities, taken, floor_index, "core", "ledger_core", core_cell)
        resource_points.append(core_cell)

    if placement_stats["lowest_accepted_min_distance"] is None:
        placement_stats["lowest_accepted_min_distance"] = PRIMARY_PLACEMENT_MIN_DISTANCE
    if placement_stats["lowest_accepted_structural_min_distance"] is None:
        placement_stats["lowest_accepted_structural_min_distance"] = STRUCTURAL_PLACEMENT_MIN_DISTANCE
    space_stats["placement"] = placement_stats

    floor = {
        "id": f"f{floor_index}",
        "name": generated_floor_name(floor_index, floor_count, stage),
        "index": floor_index,
        "grid": ["".join(row) for row in grid],
        "entities": sorted(entities, key=lambda entity: (int(entity["y"]), int(entity["x"]), entity["id"])),
        "generation": space_stats,
    }
    return floor, finish, motifs


def generate_variant(
    base_data: dict[str, Any],
    *,
    profile: str,
    seed: str,
    index: int,
    floor_count: int,
    width: int,
    height: int,
    open_ratio: float,
    boss_gate_mode: str,
    space_style: str,
    loop_budget: int,
) -> dict[str, Any]:
    rng = random.Random(stable_int_seed(seed, profile, index))
    width, height = normalize_grid_size(width, height)
    entry = (1, height // 2)
    previous_finish: tuple[int, int] | None = None
    floors: list[dict[str, Any]] = []
    motifs: list[str] = []
    for floor_index in range(1, floor_count + 1):
        stage = floor_stage(floor_index, floor_count)
        floor, finish, floor_motifs = generate_floor(
            profile=profile,
            floor_index=floor_index,
            floor_count=floor_count,
            stage=stage,
            width=width,
            height=height,
            rng=rng,
            previous_finish=previous_finish,
            next_entry=entry,
            open_ratio=open_ratio,
            boss_gate_mode=boss_gate_mode,
            space_style=space_style,
            loop_budget=loop_budget,
        )
        floors.append(floor)
        motifs.extend(floor_motifs)
        previous_finish = finish

    data = copy.deepcopy(base_data)
    variant_id = f"ledger_tower_generated_{profile}_{index:03d}"
    data["metadata"] = {
        "id": variant_id,
        "variant": f"generated_{profile}",
        "title": f"Ledger Tower: Generated {profile.replace('_', ' ').title()} {index:03d}",
        "summary": PROFILE_DESCRIPTIONS[profile],
        "grid": {"width": width, "height": height, "per_floor": False},
        "generation": {
            "generator": GENERATOR_ID,
            "seed": seed,
            "profile": profile,
            "candidate_index": index,
            "floor_count": floor_count,
            "target_open_ratio": open_ratio,
            "boss_gate_mode": boss_gate_mode,
            "space_style": space_style,
            "loop_budget": loop_budget,
            "average_open_ratio": round(
                sum(float(floor.get("generation", {}).get("open_ratio", 0.0)) for floor in floors) / max(1, len(floors)),
                3,
            ),
            "motifs": motifs,
        },
    }
    data["initial_state"] = {
        **copy.deepcopy(base_data["initial_state"]),
        "floor": "f1",
        "position": list(entry),
    }
    data["floors"] = floors
    return data


def floor_entry_points(data: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    entries: dict[str, list[tuple[int, int]]] = {}
    initial = data["initial_state"]
    entries.setdefault(initial["floor"], []).append(tuple(initial["position"]))
    for floor in data["floors"]:
        for entity in floor.get("entities", []):
            if entity["type"] == "stairs":
                entries.setdefault(entity["to_floor"], []).append(tuple(entity["to_position"]))
    return entries


def static_reachable(floor: dict[str, Any], starts: list[tuple[int, int]], blocked: set[tuple[int, int]] | None = None) -> set[tuple[int, int]]:
    blocked = blocked or set()
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for start in starts:
        if not ledger_game.is_wall(floor, *start) and start not in blocked:
            queue.append(start)
            seen.add(start)
    while queue:
        point = queue.popleft()
        for neighbor in adjacent(point):
            if neighbor in seen or neighbor in blocked:
                continue
            if ledger_game.is_wall(floor, *neighbor):
                continue
            seen.add(neighbor)
            queue.append(neighbor)
    return seen


def validate_map(data: dict[str, Any], *, require_boss_cut: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    floor_ids = {floor["id"] for floor in data.get("floors", [])}
    entries = floor_entry_points(data)

    if data["initial_state"]["floor"] not in floor_ids:
        errors.append("initial_state.floor does not reference a known floor")

    for floor in data.get("floors", []):
        floor_id = floor["id"]
        grid = floor.get("grid", [])
        if not grid:
            errors.append(f"{floor_id}: empty grid")
            continue
        width = len(grid[0])
        if any(len(row) != width for row in grid):
            errors.append(f"{floor_id}: grid rows are not rectangular")
            continue
        if width < 3 or len(grid) < 3:
            errors.append(f"{floor_id}: grid too small")
        occupied: dict[tuple[int, int], str] = {}
        for entity in floor.get("entities", []):
            point = (int(entity["x"]), int(entity["y"]))
            if ledger_game.is_wall(floor, *point):
                errors.append(f"{floor_id}:{entity['id']} is out of bounds or on a wall at {point}")
            if point in occupied:
                errors.append(f"{floor_id}:{entity['id']} overlaps {occupied[point]} at {point}")
            occupied[point] = entity["id"]
            if entity["type"] == "item" and entity["item"] not in data["items"]:
                errors.append(f"{floor_id}:{entity['id']} references unknown item {entity['item']}")
            if entity["type"] == "enemy" and entity["enemy"] not in data["enemies"]:
                errors.append(f"{floor_id}:{entity['id']} references unknown enemy {entity['enemy']}")
            if entity["type"] == "door" and entity["key"] not in data["initial_state"]["keys"]:
                errors.append(f"{floor_id}:{entity['id']} references unknown key {entity['key']}")
            if entity["type"] == "shop" and entity["shop"] not in data["shops"]:
                errors.append(f"{floor_id}:{entity['id']} references unknown shop {entity['shop']}")
            if entity["type"] == "stairs":
                target_floor = entity["to_floor"]
                target = tuple(entity["to_position"])
                if target_floor not in floor_ids:
                    errors.append(f"{floor_id}:{entity['id']} targets unknown floor {target_floor}")
                else:
                    target_grid = next(item for item in data["floors"] if item["id"] == target_floor)
                    if ledger_game.is_wall(target_grid, *target):
                        errors.append(f"{floor_id}:{entity['id']} targets wall/out-of-bounds {target_floor}{target}")

        starts = entries.get(floor_id, [])
        reachable = static_reachable(floor, starts)
        for entity in floor.get("entities", []):
            point = (int(entity["x"]), int(entity["y"]))
            if point not in reachable:
                warnings.append(f"{floor_id}:{entity['id']} is not statically reachable from known entries")

        boss = next((entity for entity in floor.get("entities", []) if entity["id"] == f"{floor_id}_boss"), None)
        exit_like = [
            entity
            for entity in floor.get("entities", [])
            if entity["type"] == "exit" or (entity["type"] == "stairs" and entity["id"].endswith("_up"))
        ]
        if floor_id == data["initial_state"]["floor"]:
            forward_starts = [tuple(data["initial_state"]["position"])]
        else:
            down = next((entity for entity in floor.get("entities", []) if entity["id"].endswith("_down")), None)
            forward_starts = [(int(down["x"]), int(down["y"]))] if down else starts
        if require_boss_cut and boss and exit_like and forward_starts:
            blocked = {(int(boss["x"]), int(boss["y"]))}
            without_boss = static_reachable(floor, forward_starts, blocked)
            for target_entity in exit_like:
                target = (int(target_entity["x"]), int(target_entity["y"]))
                if target in without_boss:
                    warnings.append(f"{floor_id}:{boss['id']} is not a structural cut point")
    return errors, warnings


def state_key(state: dict[str, Any]) -> tuple[Any, ...]:
    return (
        state["floor"],
        tuple(state["position"]),
        int(state["hp"]),
        int(state["atk"]),
        int(state["def"]),
        int(state["gold"]),
        tuple(sorted((key, int(value)) for key, value in state["keys"].items())),
        tuple(sorted(state.get("inventory", []))),
        tuple(sorted(state.get("cleared", []))),
        bool(state.get("done")),
        bool(state.get("victory")),
    )


def direction_between(start: tuple[int, int], end: tuple[int, int]) -> str:
    sx, sy = start
    ex, ey = end
    if ex == sx + 1 and ey == sy:
        return "east"
    if ex == sx - 1 and ey == sy:
        return "west"
    if ex == sx and ey == sy + 1:
        return "south"
    if ex == sx and ey == sy - 1:
        return "north"
    raise ValueError(f"non-adjacent path step: {start} -> {end}")


def active_entity_points(data: dict[str, Any], state: dict[str, Any], floor_id: str) -> dict[tuple[int, int], dict[str, Any]]:
    return {
        (int(entity["x"]), int(entity["y"])): entity
        for entity in ledger_game.entities_on_floor(data, state, floor_id)
    }


def shortest_paths_to_entities(data: dict[str, Any], state: dict[str, Any]) -> list[tuple[str, list[str]]]:
    floor_id = state["floor"]
    floor = ledger_game.floor_by_id(data)[floor_id]
    start = tuple(state["position"])
    active = active_entity_points(data, state, floor_id)
    targets = set(active)
    targets.discard(start)
    if not targets:
        return []

    queue: deque[tuple[int, int]] = deque([start])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    found: list[tuple[str, list[str]]] = []

    while queue:
        point = queue.popleft()
        if point in targets:
            path: list[tuple[int, int]] = []
            cursor: tuple[int, int] | None = point
            while cursor is not None:
                path.append(cursor)
                cursor = previous[cursor]
            path.reverse()
            commands = [f"move {direction_between(a, b)}" for a, b in zip(path, path[1:])]
            entity = active[point]
            found.append((f"{entity['id']}@{point}", commands))
            continue
        for neighbor in adjacent(point):
            if neighbor in previous:
                continue
            if ledger_game.is_wall(floor, *neighbor):
                continue
            entity = active.get(neighbor)
            if entity and neighbor not in targets and entity["type"] != "shop":
                continue
            if entity and neighbor != start and entity["type"] not in {"shop"} and neighbor not in targets:
                continue
            previous[neighbor] = point
            queue.append(neighbor)
    return sorted(found, key=lambda item: (len(item[1]), item[0]))


def available_macro_actions(data: dict[str, Any], state: dict[str, Any]) -> list[tuple[str, list[str]]]:
    actions = shortest_paths_to_entities(data, state)
    if ledger_game.current_shop_entity(state, data):
        for offer_id in ("attack", "defense", "hp"):
            actions.append((f"buy:{offer_id}", [f"buy {offer_id}"]))
    return actions


def route_result(state: dict[str, Any], data: dict[str, Any], goal: dict[str, Any], commands: list[str]) -> RouteResult:
    payload = ledger_game.score(state, data, goal)
    metrics = payload["metrics"]
    return RouteResult(
        reward=int(payload["reward"]),
        route_score=int(metrics["route_score"]),
        moves=int(metrics["moves"]),
        hp=int(metrics["hp"]),
        atk=int(metrics["atk"]),
        defense=int(metrics["def"]),
        gold=int(metrics["gold"]),
        victory=bool(metrics["victory"]),
        goal_achieved=payload.get("goal_achieved"),
        commands=list(commands),
        cleared=list(state.get("cleared", [])),
    )


def priority_for_state(state: dict[str, Any], data: dict[str, Any], goal: dict[str, Any], budget: int) -> float:
    payload = ledger_game.score(state, data, goal)
    metrics = payload["metrics"]
    remaining = max(0, budget - int(metrics["moves"]))
    return (
        float(payload["reward"])
        + int(metrics["floor_number"]) * 1200
        + int(metrics["artifacts"]) * 3500
        + (5000 if metrics["victory"] else 0)
        + remaining * 20
    )


def solve_candidate(
    data: dict[str, Any],
    *,
    budget: int,
    beam_width: int,
    max_expansions: int,
    keep_routes: int,
    goal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    goal = goal or DEFAULT_GOAL
    start = ledger_game.fresh_state(data, budget={"limit": budget}, data_path=None)
    heap: list[tuple[float, int, dict[str, Any], list[str]]] = []
    counter = 0
    heapq.heappush(heap, (-priority_for_state(start, data, goal, budget), counter, start, []))
    best_seen: dict[tuple[Any, ...], int] = {state_key(start): 0}
    successes: list[RouteResult] = []
    best_partial = route_result(start, data, goal, [])
    expansions = 0

    while heap and expansions < max_expansions:
        priority, _, state, commands = heapq.heappop(heap)
        expansions += 1
        current_result = route_result(state, data, goal, commands)
        if current_result.reward > best_partial.reward:
            best_partial = current_result
        if current_result.goal_achieved is True and current_result.moves <= budget:
            successes.append(current_result)
            successes = sorted(successes, key=lambda result: (result.reward, result.route_score), reverse=True)[:keep_routes]
            continue
        if int(state.get("moves", 0)) >= budget or state.get("done"):
            continue

        for label, action_commands in available_macro_actions(data, state):
            del label
            next_state = copy.deepcopy(state)
            next_commands = list(commands)
            before_moves = int(next_state.get("moves", 0))
            for command in action_commands:
                _, _message = ledger_game.execute(command, next_state, data)
                next_commands.append(command)
                if next_state.get("done"):
                    break
            after_moves = int(next_state.get("moves", 0))
            if after_moves <= before_moves:
                continue
            if after_moves > budget:
                continue
            key = state_key(next_state)
            previous_moves = best_seen.get(key)
            if previous_moves is not None and previous_moves <= after_moves:
                continue
            best_seen[key] = after_moves
            counter += 1
            heapq.heappush(
                heap,
                (-priority_for_state(next_state, data, goal, budget), counter, next_state, next_commands),
            )
        if len(heap) > beam_width * 4:
            heap = heapq.nsmallest(beam_width, heap)
            heapq.heapify(heap)

    successes = sorted(successes, key=lambda result: (result.reward, result.route_score), reverse=True)[:keep_routes]
    route_scores = [result.route_score for result in successes]
    shapes = {
        (
            tuple(sorted(item for item in result.cleared if "_boss" in item or "_side_" in item or "_branch" in item)),
            result.moves,
        )
        for result in successes
    }
    return {
        "budget": budget,
        "beam_width": beam_width,
        "max_expansions": max_expansions,
        "expansions": expansions,
        "visited_states": len(best_seen),
        "success_count": len(successes),
        "playable": bool(successes),
        "best": route_to_dict(successes[0]) if successes else None,
        "best_partial": route_to_dict(best_partial),
        "route_score_spread": max(route_scores) - min(route_scores) if len(route_scores) >= 2 else 0,
        "distinct_route_shapes": len(shapes),
        "routes": [route_to_dict(result) for result in successes],
    }


def route_to_dict(result: RouteResult) -> dict[str, Any]:
    return {
        "reward": result.reward,
        "route_score": result.route_score,
        "moves": result.moves,
        "hp": result.hp,
        "atk": result.atk,
        "def": result.defense,
        "gold": result.gold,
        "victory": result.victory,
        "goal_achieved": result.goal_achieved,
        "commands": result.commands,
        "cleared": result.cleared,
    }


def ranking_score(solver: dict[str, Any], validation_errors: list[str]) -> float:
    if validation_errors or not solver.get("playable"):
        return 0.0
    best = solver["best"] or {}
    return (
        float(best.get("route_score", 0))
        + float(solver.get("route_score_spread", 0)) * 0.5
        + float(solver.get("distinct_route_shapes", 0)) * 120.0
        - max(0, int(best.get("moves", 0)) - int(solver.get("budget", 0))) * 500.0
    )


def generate_records(args: argparse.Namespace) -> list[CandidateRecord]:
    base_data = load_json(args.base_data)
    if args.floors < 2:
        raise SystemExit("--floors must be at least 2")
    profiles = [profile.strip() for profile in args.profiles.split(",") if profile.strip()]
    unknown = [profile for profile in profiles if profile not in PROFILE_DESCRIPTIONS]
    if unknown:
        raise SystemExit(f"Unknown profile(s): {', '.join(unknown)}")

    records: list[CandidateRecord] = []
    for profile in profiles:
        for index in range(1, args.count + 1):
            data = generate_variant(
                base_data,
                profile=profile,
                seed=args.seed,
                index=index,
                floor_count=args.floors,
                width=args.width,
                height=args.height,
                open_ratio=args.open_ratio,
                boss_gate_mode=args.boss_gate_mode,
                space_style=args.space_style,
                loop_budget=args.loop_budget,
            )
            errors, warnings = validate_map(data, require_boss_cut=args.boss_gate_mode == "preserve")
            solver = (
                solve_candidate(
                    data,
                    budget=args.budget,
                    beam_width=args.beam_width,
                    max_expansions=args.max_expansions,
                    keep_routes=args.keep_routes,
                    goal=DEFAULT_GOAL,
                )
                if not errors
                else {
                    "budget": args.budget,
                    "playable": False,
                    "success_count": 0,
                    "best": None,
                    "best_partial": None,
                    "route_score_spread": 0,
                    "distinct_route_shapes": 0,
                    "expansions": 0,
                    "visited_states": 0,
                }
            )
            records.append(
                CandidateRecord(
                    profile=profile,
                    seed=args.seed,
                    index=index,
                    data=data,
                    validation_errors=errors,
                    validation_warnings=warnings,
                    solver=solver,
                    ranking_score=ranking_score(solver, errors),
                )
            )
    return records


def candidate_slug(record: CandidateRecord) -> str:
    return f"{record.profile}_{record.index:03d}"


def select_kept(records: list[CandidateRecord], keep: int, keep_per_profile: int) -> list[CandidateRecord]:
    ranked = sorted(records, key=lambda record: record.ranking_score, reverse=True)
    playable = [record for record in ranked if record.ranking_score > 0]
    kept: list[CandidateRecord] = []
    kept_ids: set[int] = set()
    for profile in sorted({record.profile for record in records}):
        profile_records = [record for record in playable if record.profile == profile]
        for record in profile_records[:keep_per_profile]:
            if len(kept) >= keep:
                return kept
            kept.append(record)
            kept_ids.add(id(record))
    for record in playable:
        if len(kept) >= keep:
            break
        if id(record) in kept_ids:
            continue
        kept.append(record)
        kept_ids.add(id(record))
    return kept


def write_outputs(records: list[CandidateRecord], out_dir: Path, keep: int, keep_per_profile: int) -> list[CandidateRecord]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ranked = sorted(records, key=lambda record: record.ranking_score, reverse=True)
    kept = select_kept(records, keep, keep_per_profile)

    summary = {
        "generator": GENERATOR_ID,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "candidate_count": len(records),
        "kept_count": len(kept),
        "profiles": sorted({record.profile for record in records}),
        "records": [record_summary(record) for record in ranked],
    }
    write_json(out_dir / "summary.json", summary)
    (out_dir / "report.md").write_text(render_markdown_report(ranked, kept), encoding="utf-8")

    for record in kept:
        slug = candidate_slug(record)
        write_json(out_dir / f"{slug}.json", record.data)
        best = record.solver.get("best") or {}
        if best.get("commands"):
            route = "\n".join(best["commands"]) + "\n"
            (out_dir / f"{slug}_best_route.txt").write_text(route, encoding="utf-8")
    return kept


def record_summary(record: CandidateRecord) -> dict[str, Any]:
    best = record.solver.get("best") or {}
    return {
        "profile": record.profile,
        "index": record.index,
        "variant": record.data.get("metadata", {}).get("variant"),
        "ranking_score": round(record.ranking_score, 2),
        "errors": record.validation_errors,
        "warnings": record.validation_warnings,
        "playable": bool(record.solver.get("playable")),
        "success_count": int(record.solver.get("success_count", 0)),
        "route_score_spread": int(record.solver.get("route_score_spread", 0)),
        "distinct_route_shapes": int(record.solver.get("distinct_route_shapes", 0)),
        "average_open_ratio": record.data.get("metadata", {}).get("generation", {}).get("average_open_ratio"),
        "floor_count": record.data.get("metadata", {}).get("generation", {}).get("floor_count"),
        "space_style": record.data.get("metadata", {}).get("generation", {}).get("space_style"),
        "boss_gate_mode": record.data.get("metadata", {}).get("generation", {}).get("boss_gate_mode"),
        "best_reward": best.get("reward"),
        "best_route_score": best.get("route_score"),
        "best_moves": best.get("moves"),
        "best_hp": best.get("hp"),
        "best_atk": best.get("atk"),
        "best_def": best.get("def"),
        "best_gold": best.get("gold"),
        "expansions": int(record.solver.get("expansions", 0)),
        "visited_states": int(record.solver.get("visited_states", 0)),
    }


def render_markdown_report(ranked: list[CandidateRecord], kept: list[CandidateRecord]) -> str:
    lines = [
        "# Ledger Tower Generated Variant Report",
        "",
        f"Generator: `{GENERATOR_ID}`",
        f"Candidates: `{len(ranked)}`",
        f"Kept: `{len(kept)}`",
        "",
        "## Kept Candidates",
        "",
        "| candidate | score | floors | style | open | best route_score | reward | moves | spread | shapes | warnings |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    if kept:
        for record in kept:
            best = record.solver.get("best") or {}
            warnings = "; ".join(record.validation_warnings[:2])
            generation = record.data.get("metadata", {}).get("generation", {})
            average_open = generation.get("average_open_ratio")
            floor_count = generation.get("floor_count")
            space_style = generation.get("space_style")
            lines.append(
                "| "
                + " | ".join(
                    [
                        candidate_slug(record),
                        f"{record.ranking_score:.1f}",
                        str(floor_count),
                        str(space_style),
                        str(average_open),
                        str(best.get("route_score")),
                        str(best.get("reward")),
                        str(best.get("moves")),
                        str(record.solver.get("route_score_spread", 0)),
                        str(record.solver.get("distinct_route_shapes", 0)),
                        warnings or "-",
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | 0 | - | - | - | - | - | - | - | - | no playable candidates |")
    lines.extend([
        "",
        "## All Candidates",
        "",
        "| candidate | playable | ranking | best route_score | best moves | successes | errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ])
    for record in ranked:
        best = record.solver.get("best") or {}
        errors = "; ".join(record.validation_errors[:2])
        lines.append(
            "| "
            + " | ".join(
                [
                    candidate_slug(record),
                    "yes" if record.solver.get("playable") else "no",
                    f"{record.ranking_score:.1f}",
                    str(best.get("route_score")),
                    str(best.get("moves")),
                    str(record.solver.get("success_count", 0)),
                    errors or "-",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and score Ledger Tower map variants.")
    parser.add_argument("--base-data", type=Path, default=DEFAULT_BASE_DATA)
    parser.add_argument("--profiles", default="branchy_score,shop_timing,key_pressure")
    parser.add_argument("--count", type=int, default=4, help="Candidates per profile.")
    parser.add_argument("--seed", default="ledger-variant-v1")
    parser.add_argument("--floors", type=int, default=6, help="Number of generated tower floors.")
    parser.add_argument("--width", type=int, default=11)
    parser.add_argument("--height", type=int, default=11)
    parser.add_argument("--open-ratio", type=float, default=0.42, help="Target average open-cell ratio for generated floors.")
    parser.add_argument("--boss-gate-mode", choices=["relaxed", "preserve"], default="relaxed", help="Use preserve only for variants that require every floor boss to be a structural cut point.")
    parser.add_argument("--space-style", choices=["hybrid", "tree", "patch"], default="hybrid", help="Grid expansion style: hybrid rooms/corridors, tree frontier, or broad room patches.")
    parser.add_argument("--loop-budget", type=int, default=1, help="Short loop cells to add per floor for relaxed hybrid maps.")
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--beam-width", type=int, default=1600)
    parser.add_argument("--max-expansions", type=int, default=30000)
    parser.add_argument("--keep-routes", type=int, default=8)
    parser.add_argument("--keep", type=int, default=5, help="Number of candidate JSON files to write.")
    parser.add_argument("--keep-per-profile", type=int, default=1, help="Playable candidates to keep per requested profile before filling by rank.")
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def default_out_dir() -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return PLAYGROUND_ROOT / "logs" / "ledger_variant_generation" / stamp


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir or default_out_dir()
    records = generate_records(args)
    kept = write_outputs(records, out_dir, args.keep, args.keep_per_profile)
    print(f"Generated {len(records)} candidates; kept {len(kept)}.")
    print(f"Report: {out_dir / 'report.md'}")
    print(f"Summary: {out_dir / 'summary.json'}")
    for record in kept:
        best = record.solver.get("best") or {}
        print(
            f"- {candidate_slug(record)} route_score={best.get('route_score')} "
            f"reward={best.get('reward')} moves={best.get('moves')} "
            f"spread={record.solver.get('route_score_spread')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
