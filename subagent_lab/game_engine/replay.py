from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from .snapshot import Snapshot


StateT = TypeVar("StateT")


@dataclass(frozen=True)
class ReplayStep:
    raw_command: str
    snapshot: Snapshot
    status: str
    terminal: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_command": self.raw_command,
            "snapshot": self.snapshot.to_dict(),
            "status": self.status,
            "terminal": self.terminal,
        }


@dataclass(frozen=True)
class ReplaySession:
    initial_snapshot: Snapshot
    steps: tuple[ReplayStep, ...]
    final_snapshot: Snapshot
    terminal_status: str
    terminal: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "initial_snapshot": self.initial_snapshot.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "final_snapshot": self.final_snapshot.to_dict(),
            "terminal_status": self.terminal_status,
            "terminal": self.terminal,
        }


def run_command_replay(
    initial_state: StateT,
    commands: Iterable[str],
    apply_command: Callable[[StateT, str], object],
    snapshot_state: Callable[[StateT], Snapshot],
) -> ReplaySession:
    initial_snapshot = snapshot_state(initial_state)
    last_snapshot = initial_snapshot
    steps: list[ReplayStep] = []

    if not _is_terminal_snapshot(initial_snapshot):
        for raw_command in commands:
            apply_command(initial_state, raw_command)
            last_snapshot = snapshot_state(initial_state)
            steps.append(
                ReplayStep(
                    raw_command=raw_command,
                    snapshot=last_snapshot,
                    status=last_snapshot.status,
                    terminal=_is_terminal_snapshot(last_snapshot),
                )
            )
            if _is_terminal_snapshot(last_snapshot):
                break

    return ReplaySession(
        initial_snapshot=initial_snapshot,
        steps=tuple(steps),
        final_snapshot=last_snapshot,
        terminal_status=last_snapshot.status,
        terminal=_is_terminal_snapshot(last_snapshot),
    )


def _is_terminal_snapshot(snapshot: Snapshot) -> bool:
    return snapshot.terminal or snapshot.status != "playing"


__all__ = ["ReplaySession", "ReplayStep", "run_command_replay"]
