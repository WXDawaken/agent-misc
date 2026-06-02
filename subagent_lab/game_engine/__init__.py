"""Reusable Python grid-game engine primitives for subagent experiments."""

from .commands import (
    CARDINAL_ALIASES,
    CARDINAL_DELTAS,
    CommandArgumentSpec,
    CommandSpec,
    export_command_manifest,
    normalize_cardinal_token,
    normalize_command_token,
    parse_command,
)
from .grid import Position, RectGrid
from .logging import push_capped_message
from .replay import ReplaySession, ReplayStep, run_command_replay
from .rendering import render_rect_grid
from .snapshot import (
    Snapshot,
    SnapshotActor,
    SnapshotAnnotation,
    SnapshotLayer,
    SnapshotPosition,
    SnapshotSize,
)
from .theme import REQUIRED_RENDER_THEME_SLOTS, RenderTheme, RenderThemeSlot

__all__ = [
    "CARDINAL_ALIASES",
    "CARDINAL_DELTAS",
    "CommandArgumentSpec",
    "CommandSpec",
    "export_command_manifest",
    "normalize_cardinal_token",
    "normalize_command_token",
    "parse_command",
    "Position",
    "RectGrid",
    "ReplaySession",
    "ReplayStep",
    "push_capped_message",
    "render_rect_grid",
    "run_command_replay",
    "Snapshot",
    "SnapshotActor",
    "SnapshotAnnotation",
    "SnapshotLayer",
    "SnapshotPosition",
    "SnapshotSize",
    "REQUIRED_RENDER_THEME_SLOTS",
    "RenderTheme",
    "RenderThemeSlot",
]
