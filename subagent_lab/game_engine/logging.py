from __future__ import annotations

from collections.abc import MutableSequence


def push_capped_message(messages: MutableSequence[str], message: str, *, limit: int = 6) -> None:
    messages.append(message)
    if len(messages) > limit:
        del messages[:-limit]
