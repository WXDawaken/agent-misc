"""Serializable render-theme primitives for lightweight text-grid clients.

Emoji and other wide glyphs remain terminal-dependent. This module carries
theme metadata and notes, but it does not try to normalize Unicode cell width.
"""

from __future__ import annotations

from dataclasses import dataclass


REQUIRED_RENDER_THEME_SLOTS = (
    "empty",
    "player",
    "drone",
    "salvage",
    "hazard",
    "wall",
    "exit",
)


@dataclass(frozen=True)
class RenderThemeSlot:
    slot_id: str
    token: str
    label: str
    description: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "id": self.slot_id,
            "token": self.token,
            "label": self.label,
        }
        if self.description:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class RenderTheme:
    theme_id: str
    slots: tuple[RenderThemeSlot, ...]
    legend_order: tuple[str, ...] = ()
    title: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.theme_id:
            raise ValueError("RenderTheme.theme_id must be a non-empty string.")

        slot_by_id: dict[str, RenderThemeSlot] = {}
        normalized_slots: list[RenderThemeSlot] = []

        for slot in self.slots:
            _validate_slot(slot)
            if slot.slot_id in slot_by_id:
                raise ValueError(f"Duplicate render theme slot {slot.slot_id!r}.")
            slot_by_id[slot.slot_id] = slot
            normalized_slots.append(slot)

        missing = [slot_id for slot_id in REQUIRED_RENDER_THEME_SLOTS if slot_id not in slot_by_id]
        if missing:
            raise ValueError(
                "RenderTheme is missing required slots: " + ", ".join(missing) + "."
            )

        if self.title is not None and not self.title:
            raise ValueError("RenderTheme.title must be a non-empty string when provided.")

        resolved_legend_order = self.legend_order or tuple(
            slot.slot_id for slot in normalized_slots if slot.slot_id != "empty"
        )
        normalized_legend_order: list[str] = []
        seen_legend_slots: set[str] = set()
        for slot_id in resolved_legend_order:
            if slot_id not in slot_by_id:
                raise ValueError(f"Legend slot {slot_id!r} is not defined on this RenderTheme.")
            if slot_id in seen_legend_slots:
                raise ValueError(f"Legend slot {slot_id!r} appears more than once.")
            normalized_legend_order.append(slot_id)
            seen_legend_slots.add(slot_id)

        object.__setattr__(self, "slots", tuple(normalized_slots))
        object.__setattr__(self, "legend_order", tuple(normalized_legend_order))
        object.__setattr__(self, "notes", _normalize_string_tuple(self.notes, field_name="notes"))

    @property
    def legend_slots(self) -> tuple[RenderThemeSlot, ...]:
        slot_by_id = {slot.slot_id: slot for slot in self.slots}
        return tuple(slot_by_id[slot_id] for slot_id in self.legend_order)

    def slot_for(self, slot_id: str) -> RenderThemeSlot:
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(f"Unknown render theme slot {slot_id!r}.")

    def token_for(self, slot_id: str) -> str:
        return self.slot_for(slot_id).token

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.theme_id,
            "slots": [slot.to_dict() for slot in self.slots],
            "legend": [slot.to_dict() for slot in self.legend_slots],
        }
        if self.title:
            payload["title"] = self.title
        if self.notes:
            payload["notes"] = list(self.notes)
        return payload


def _validate_slot(slot: RenderThemeSlot) -> None:
    if not slot.slot_id:
        raise ValueError("RenderThemeSlot.slot_id must be a non-empty string.")
    if not slot.token:
        raise ValueError(f"RenderThemeSlot {slot.slot_id!r} must define a non-empty token.")
    if not slot.label:
        raise ValueError(f"RenderThemeSlot {slot.slot_id!r} must define a non-empty label.")
    if slot.description is not None and not slot.description:
        raise ValueError(
            f"RenderThemeSlot {slot.slot_id!r} description must be non-empty when provided."
        )


def _normalize_string_tuple(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"RenderTheme {field_name} values must be strings.")
        normalized.append(value)
    return tuple(normalized)


__all__ = ["REQUIRED_RENDER_THEME_SLOTS", "RenderTheme", "RenderThemeSlot"]
