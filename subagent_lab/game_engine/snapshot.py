from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from .grid import Position, RectGrid


@dataclass(frozen=True, order=True)
class SnapshotPosition:
    x: int
    y: int

    @classmethod
    def from_position(cls, position: Position) -> "SnapshotPosition":
        return cls(x=position.x, y=position.y)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class SnapshotSize:
    width: int
    height: int

    @classmethod
    def from_grid(cls, grid: RectGrid) -> "SnapshotSize":
        return cls(width=grid.width, height=grid.height)

    def to_dict(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class SnapshotLayer:
    name: str
    positions: tuple[SnapshotPosition, ...]

    @classmethod
    def from_positions(
        cls,
        name: str,
        positions: Iterable[Position | SnapshotPosition],
    ) -> "SnapshotLayer":
        return cls(name=name, positions=_normalize_positions(positions))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "positions": [position.to_dict() for position in self.positions],
        }


@dataclass(frozen=True)
class SnapshotActor:
    actor_id: str
    kind: str
    position: SnapshotPosition
    values: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def from_position(
        cls,
        actor_id: str,
        kind: str,
        position: Position | SnapshotPosition,
        *,
        values: Mapping[str, object] | None = None,
    ) -> "SnapshotActor":
        return cls(
            actor_id=actor_id,
            kind=kind,
            position=_coerce_position(position),
            values={} if values is None else dict(values),
        )

    def to_dict(self) -> dict[str, object]:
        actor = {
            "id": self.actor_id,
            "kind": self.kind,
            "position": self.position.to_dict(),
        }
        if self.values:
            actor["values"] = _normalize_mapping(self.values)
        return actor


@dataclass(frozen=True)
class SnapshotAnnotation:
    position: SnapshotPosition
    terrain_tags: tuple[str, ...] = ()
    actor_tags: tuple[str, ...] = ()
    overlay_flags: tuple[str, ...] = ()
    values: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def from_position(
        cls,
        position: Position | SnapshotPosition,
        *,
        terrain_tags: Iterable[str] = (),
        actor_tags: Iterable[str] = (),
        overlay_flags: Iterable[str] = (),
        values: Mapping[str, object] | None = None,
    ) -> "SnapshotAnnotation":
        return cls(
            position=_coerce_position(position),
            terrain_tags=_normalize_string_tuple(terrain_tags, field_name="terrain_tags"),
            actor_tags=_normalize_string_tuple(actor_tags, field_name="actor_tags"),
            overlay_flags=_normalize_string_tuple(overlay_flags, field_name="overlay_flags"),
            values={} if values is None else dict(values),
        )

    def to_dict(self) -> dict[str, object]:
        annotation = {
            "position": self.position.to_dict(),
        }
        if self.terrain_tags:
            annotation["terrain_tags"] = list(
                _normalize_string_tuple(self.terrain_tags, field_name="terrain_tags")
            )
        if self.actor_tags:
            annotation["actor_tags"] = list(
                _normalize_string_tuple(self.actor_tags, field_name="actor_tags")
            )
        if self.overlay_flags:
            annotation["overlay_flags"] = list(
                _normalize_string_tuple(self.overlay_flags, field_name="overlay_flags")
            )
        if self.values:
            annotation["values"] = _normalize_mapping(self.values)
        return annotation


@dataclass(frozen=True)
class Snapshot:
    board: SnapshotSize
    layers: tuple[SnapshotLayer, ...]
    actors: tuple[SnapshotActor, ...] = ()
    messages: tuple[str, ...] = ()
    hud: Mapping[str, object] = field(default_factory=dict)
    status: str = "playing"
    terminal: bool = False
    annotations: tuple[SnapshotAnnotation, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = {
            "board": self.board.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "actors": [actor.to_dict() for actor in self.actors],
            "messages": list(self.messages),
            "hud": _normalize_mapping(self.hud),
            "status": self.status,
            "terminal": self.terminal,
        }
        if self.annotations:
            payload["annotations"] = [
                annotation.to_dict()
                for annotation in _normalize_annotations(self.annotations)
            ]
        return payload


def _coerce_position(position: Position | SnapshotPosition) -> SnapshotPosition:
    if isinstance(position, SnapshotPosition):
        return position
    return SnapshotPosition.from_position(position)


def _normalize_positions(
    positions: Iterable[Position | SnapshotPosition],
) -> tuple[SnapshotPosition, ...]:
    return tuple(sorted(_coerce_position(position) for position in positions))


def _normalize_annotations(
    annotations: Iterable[SnapshotAnnotation],
) -> tuple[SnapshotAnnotation, ...]:
    return tuple(sorted(annotations, key=_annotation_sort_key))


def _annotation_sort_key(annotation: SnapshotAnnotation) -> tuple[int, int, str]:
    return (
        annotation.position.x,
        annotation.position.y,
        json.dumps(annotation.to_dict(), sort_keys=True, separators=(",", ":")),
    )


def _normalize_string_tuple(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"Snapshot {field_name} values must be strings.")
        normalized.append(value)
    return tuple(sorted(normalized))


def _normalize_mapping(values: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key in sorted(values):
        normalized[key] = _normalize_json_value(values[key])
    return normalized


def _normalize_json_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("Snapshot metadata keys must be strings.")
            normalized[key] = _normalize_json_value(value[key])
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item) for item in value]
    raise TypeError(f"Snapshot metadata value {value!r} is not JSON-serializable.")
