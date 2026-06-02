"""Action plan model."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PreviewSection(BaseModel):
    id: str
    title: str
    lines: list[str] = Field(default_factory=list)
    style: str = "bulleted"


class ConfirmationDetails(BaseModel):
    reason: str
    review_items: list[str] = Field(default_factory=list)


class ActionPlan(BaseModel):
    action_id: str
    summary: str
    risk: str
    requires_confirmation: bool
    steps: list[str] = Field(default_factory=list)
    affected_objects: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)
    preview_changes: list[str] = Field(default_factory=list)
    preview_sections: list[PreviewSection] = Field(default_factory=list)
    confirmation_details: ConfirmationDetails | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    engine_mutations: list[str] = Field(default_factory=list)
    rollback_strategy: str

    @model_validator(mode="after")
    def validate_confirmation_details_contract(self) -> "ActionPlan":
        if self.requires_confirmation and self.confirmation_details is None:
            raise ValueError(
                "confirmation_details is required when requires_confirmation is true"
            )
        return self
