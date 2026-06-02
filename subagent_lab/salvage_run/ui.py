from __future__ import annotations

from collections.abc import Mapping

from game_engine import Position, RenderTheme, RenderThemeSlot, Snapshot, SnapshotAnnotation, render_rect_grid

from .models import GameState
from .snapshot import snapshot_state


DEFAULT_THEME = "ascii"


def _theme_slot(
    slot_id: str,
    token: str,
    label: str,
    description: str | None = None,
) -> RenderThemeSlot:
    return RenderThemeSlot(slot_id=slot_id, token=token, label=label, description=description)


_THEMES = {
    "ascii": RenderTheme(
        theme_id="ascii",
        title="ASCII",
        slots=(
            _theme_slot("empty", ".", "empty"),
            _theme_slot("player", "@", "you"),
            _theme_slot("drone", "D", "drone"),
            _theme_slot("salvage", "$", "salvage"),
            _theme_slot("hazard", "!", "hazard"),
            _theme_slot("wall", "#", "wall"),
            _theme_slot("exit", "E", "exit"),
        ),
    ),
    "scanner": RenderTheme(
        theme_id="scanner",
        title="Scanner",
        slots=(
            _theme_slot("empty", ".", "clear"),
            _theme_slot("player", "@", "you"),
            _theme_slot("drone", "x", "contact"),
            _theme_slot("salvage", "+", "cache"),
            _theme_slot("hazard", "!", "hazard"),
            _theme_slot("wall", "=", "bulkhead"),
            _theme_slot("exit", ">", "extract"),
        ),
        legend_order=("player", "salvage", "exit", "drone", "hazard", "wall"),
        notes=(
            "Scanner theme keeps the board ASCII-only with terse objective and threat markers.",
        ),
    ),
    "emoji": RenderTheme(
        theme_id="emoji",
        title="Emoji",
        slots=(
            _theme_slot("empty", "⬛", "empty"),
            _theme_slot("player", "🙂", "you"),
            _theme_slot("drone", "🤖", "drone"),
            _theme_slot("salvage", "💎", "salvage"),
            _theme_slot(
                "hazard",
                "🔥",
                "hazard",
                "Terminal width may vary by font.",
            ),
            _theme_slot("wall", "🧱", "wall"),
            _theme_slot("exit", "🚪", "exit"),
        ),
        notes=(
            "Emoji and full-width glyphs may misalign in terminals without Unicode-width support.",
        ),
    ),
}
SUPPORTED_THEMES = tuple(_THEMES)


def render_game(state: GameState, *, theme: str = "ascii") -> str:
    resolved_theme = _resolve_theme(theme)
    board = _render_board(state, theme=resolved_theme)
    status_line = (
        f"Map: {state.level.name} | Turn: {state.turn} | Energy: {state.energy} | "
        f"Hull: {state.hull}/{state.max_hull} | Salvage: {state.salvage_collected}/{state.level.required_salvage} | "
        f"Score: {state.score}"
    )
    recent = "\n".join(f"- {message}" for message in state.messages[-3:]) or "- No events yet."
    lines = [status_line]
    if resolved_theme.theme_id == "scanner":
        snapshot = snapshot_state(state)
        lines.append(_scanner_summary_line(snapshot))
        lines.append(_scanner_points_of_interest_line(snapshot))
    lines.extend((_legend_line(resolved_theme), board, "Recent events:", recent))
    return "\n".join(lines)


def _resolve_theme(theme: str) -> RenderTheme:
    try:
        return _THEMES[theme]
    except KeyError as error:
        supported = ", ".join(sorted(_THEMES))
        raise ValueError(f"Unsupported theme {theme!r}. Expected one of: {supported}.") from error


def _legend_line(theme: RenderTheme) -> str:
    return "Legend: " + ", ".join(f"{slot.token} {slot.label}" for slot in theme.legend_slots)


def _scanner_summary_line(snapshot: Snapshot) -> str:
    nearest_salvage = _find_annotation(
        snapshot.annotations,
        overlay_flag="nearest_salvage",
        terrain_tag="salvage",
    )
    nearest_drone = _find_annotation(
        snapshot.annotations,
        overlay_flag="nearest_drone",
        actor_tag="drone",
    )
    exit_annotation = _find_annotation(snapshot.annotations, terrain_tag="exit")
    return "Scanner: " + " | ".join(
        (
            _format_annotation_target(
                nearest_salvage,
                value_key="salvage",
                label="cache",
                absent_text="cache clear",
            ),
            _format_annotation_target(
                nearest_drone,
                value_key="drone",
                label="contact",
                absent_text="contact none",
            ),
            _format_extract_status(exit_annotation),
        )
    )


def _scanner_points_of_interest_line(snapshot: Snapshot) -> str:
    points = sorted(
        (
            point
            for annotation in snapshot.annotations
            if (point := _scanner_point_of_interest(annotation)) is not None
        ),
        key=lambda point: (
            point["distance"],
            point["annotation"].position.y,
            point["annotation"].position.x,
            point["rank"],
        ),
    )[:3]
    if not points:
        return "POI: none"
    return "POI: " + " | ".join(
        _format_annotation_target(
            point["annotation"],
            value_key=point["value_key"],
            label=point["label"],
            absent_text=f'{point["label"]} unknown',
        )
        for point in points
    )


def _scanner_point_of_interest(
    annotation: SnapshotAnnotation,
) -> dict[str, int | str | SnapshotAnnotation] | None:
    if "point_of_interest" not in annotation.overlay_flags or "player" in annotation.actor_tags:
        return None
    for rank, (label, value_key, terrain_tag, actor_tag) in enumerate(
        (
            ("cache", "salvage", "salvage", None),
            ("contact", "drone", None, "drone"),
            ("extract", "exit", "exit", None),
            ("hazard", "hazard", "hazard", None),
        )
    ):
        if terrain_tag is not None and terrain_tag not in annotation.terrain_tags:
            continue
        if actor_tag is not None and actor_tag not in annotation.actor_tags:
            continue
        distance = _annotation_distance(annotation, value_key)
        if distance is None:
            return None
        return {
            "annotation": annotation,
            "distance": distance,
            "label": label,
            "rank": rank,
            "value_key": value_key,
        }
    return None


def _find_annotation(
    annotations: tuple[SnapshotAnnotation, ...],
    *,
    overlay_flag: str | None = None,
    terrain_tag: str | None = None,
    actor_tag: str | None = None,
) -> SnapshotAnnotation | None:
    for annotation in annotations:
        if overlay_flag is not None and overlay_flag not in annotation.overlay_flags:
            continue
        if terrain_tag is not None and terrain_tag not in annotation.terrain_tags:
            continue
        if actor_tag is not None and actor_tag not in annotation.actor_tags:
            continue
        return annotation
    return None


def _format_annotation_target(
    annotation: SnapshotAnnotation | None,
    *,
    value_key: str,
    label: str,
    absent_text: str,
) -> str:
    if annotation is None:
        return absent_text
    values = annotation.values.get(value_key)
    distance = None
    if isinstance(values, Mapping):
        raw_distance = values.get("distance_to_player")
        if isinstance(raw_distance, int):
            distance = raw_distance
    if distance is None:
        return f"{label} @ ({annotation.position.x}, {annotation.position.y})"
    return f"{label} {distance} away @ ({annotation.position.x}, {annotation.position.y})"


def _annotation_distance(annotation: SnapshotAnnotation, value_key: str) -> int | None:
    values = annotation.values.get(value_key)
    if not isinstance(values, Mapping):
        return None
    raw_distance = values.get("distance_to_player")
    if isinstance(raw_distance, int):
        return raw_distance
    return None


def _format_extract_status(annotation: SnapshotAnnotation | None) -> str:
    if annotation is None:
        return "extract unknown"
    values = annotation.values.get("exit")
    ready_for_extraction = False
    remaining_to_goal = None
    if isinstance(values, Mapping):
        ready_value = values.get("ready_for_extraction")
        if isinstance(ready_value, bool):
            ready_for_extraction = ready_value
        raw_remaining = values.get("remaining_to_goal")
        if isinstance(raw_remaining, int):
            remaining_to_goal = raw_remaining
    if ready_for_extraction or "extract_ready" in annotation.overlay_flags:
        return "extract READY"
    if remaining_to_goal is None:
        return "extract LOCKED"
    salvage_noun = "cache" if remaining_to_goal == 1 else "caches"
    return f"extract LOCKED ({remaining_to_goal} {salvage_noun} needed)"


def _render_board(state: GameState, *, theme: RenderTheme) -> str:
    drone_token = theme.token_for("drone")
    empty_token = theme.token_for("empty")
    player_token = theme.token_for("player")
    wall_token = theme.token_for("wall")
    salvage_token = theme.token_for("salvage")
    hazard_token = theme.token_for("hazard")
    exit_token = theme.token_for("exit")
    drone_positions = {position: drone_token for position in state.drones}

    def resolve_tile(position: Position) -> str:
        if position == state.player:
            return player_token
        if position in drone_positions:
            return drone_positions[position]
        if position in state.level.walls:
            return wall_token
        if position in state.salvage_remaining:
            return salvage_token
        if position in state.level.hazards:
            return hazard_token
        if position == state.level.exit_position:
            return exit_token
        return empty_token

    return render_rect_grid(
        state.level.width,
        state.level.height,
        resolve_tile,
        separator=" ",
    )
