"""Patch proposal model."""

from __future__ import annotations

from pydantic import BaseModel


class PatchProposal(BaseModel):
    patch_id: str
    action_id: str
    patch_kind: str
    target_id: str
    target_path: str
    format: str
    content: str
    apply_mode: str
