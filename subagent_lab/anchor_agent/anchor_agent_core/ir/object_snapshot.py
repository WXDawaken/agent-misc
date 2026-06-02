"""Object snapshot models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ObjectRelation(BaseModel):
    kind: str
    target_id: str
    label: str | None = None


class ObjectSnapshot(BaseModel):
    object_id: str
    engine: str
    object_kind: str
    display_name: str
    type_name: str
    path: str
    scene_path: str
    parent_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    relations: list[ObjectRelation] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    selection_state: dict[str, Any] = Field(default_factory=dict)
