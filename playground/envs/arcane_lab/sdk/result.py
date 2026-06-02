from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StepResult:
    command: str
    output: str
    observation: dict[str, Any]
    reward: int
    done: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
