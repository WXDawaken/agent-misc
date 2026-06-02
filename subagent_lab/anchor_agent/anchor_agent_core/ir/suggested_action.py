"""Suggested action model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SuggestedAction(BaseModel):
    id: str
    title: str
    intent: str
    target_ids: list[str] = Field(default_factory=list)
    confidence: float
    risk: str
    requires_confirmation: bool
    rationale: str
    preconditions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
