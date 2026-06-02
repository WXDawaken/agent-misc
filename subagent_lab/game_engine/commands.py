from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


CARDINAL_DELTAS = {
    "w": (0, -1),
    "a": (-1, 0),
    "s": (0, 1),
    "d": (1, 0),
}

CARDINAL_ALIASES = {
    "up": "w",
    "left": "a",
    "down": "s",
    "right": "d",
}


def _normalize_token(raw: str) -> str:
    return raw.strip().lower()


def normalize_cardinal_token(raw: str) -> str:
    token = _normalize_token(raw)
    return CARDINAL_ALIASES.get(token, token)


@dataclass(frozen=True)
class CommandArgumentSpec:
    name: str
    required: bool = True
    choices: tuple[str, ...] = ()
    hint: str | None = None
    aliases: tuple[tuple[str, str], ...] = ()

    @property
    def usage_fragment(self) -> str:
        return f"<{self.name}>" if self.required else f"[{self.name}]"

    def normalize_token(self, raw: str) -> str:
        alias_map = {
            _normalize_token(alias): _normalize_token(target)
            for alias, target in self.aliases
        }
        token = alias_map.get(_normalize_token(raw), _normalize_token(raw))

        if self.choices:
            normalized_choices = {_normalize_token(choice) for choice in self.choices}
            if token not in normalized_choices:
                cardinal_token = normalize_cardinal_token(token)
                if cardinal_token in normalized_choices:
                    token = cardinal_token
        return token

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "required": self.required,
        }
        if self.choices:
            payload["choices"] = list(self.choices)
        if self.hint:
            payload["hint"] = self.hint
        if self.aliases:
            payload["aliases"] = {
                _normalize_token(alias): _normalize_token(target)
                for alias, target in self.aliases
            }
        return payload


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    primary_token: str
    description: str
    aliases: tuple[str, ...] = ()
    args: tuple[CommandArgumentSpec, ...] = ()
    label: str | None = None
    hotkeys: tuple[str, ...] = ()
    category: str | None = None

    @property
    def usage(self) -> str:
        if not self.args:
            return self.primary_token
        fragments = " ".join(argument.usage_fragment for argument in self.args)
        return f"{self.primary_token} {fragments}"

    @property
    def tokens(self) -> tuple[str, ...]:
        return (self.primary_token, *self.aliases)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.command_id,
            "primary_token": self.primary_token,
            "description": self.description,
            "usage": self.usage,
        }
        if self.label:
            payload["label"] = self.label
        if self.aliases:
            payload["aliases"] = list(self.aliases)
        if self.args:
            payload["args"] = [argument.to_dict() for argument in self.args]
        if self.hotkeys:
            payload["hotkeys"] = list(self.hotkeys)
        if self.category:
            payload["category"] = self.category
        return payload


def export_command_manifest(specs: Sequence[CommandSpec]) -> list[dict[str, object]]:
    return [spec.to_dict() for spec in specs]


def normalize_command_token(raw: str, specs: Sequence[CommandSpec]) -> str:
    token = _normalize_token(raw)
    aliases = {
        _normalize_token(command_token): _normalize_token(spec.primary_token)
        for spec in specs
        for command_token in spec.tokens
    }
    return aliases.get(token, token)


def parse_command(raw: str, specs: Sequence[CommandSpec]) -> tuple[str, list[str]]:
    parts = [_normalize_token(part) for part in raw.split()]
    if not parts:
        return "", []

    command_token = normalize_command_token(parts[0], specs)
    spec = _find_command_spec(command_token, specs)
    if spec is None:
        return command_token, parts[1:]

    normalized_args = [
        _normalize_argument_token(argument, spec.args[index] if index < len(spec.args) else None)
        for index, argument in enumerate(parts[1:])
    ]
    return command_token, normalized_args


def _find_command_spec(
    normalized_command_token: str,
    specs: Sequence[CommandSpec],
) -> CommandSpec | None:
    for spec in specs:
        if _normalize_token(spec.primary_token) == normalized_command_token:
            return spec
    return None


def _normalize_argument_token(raw: str, argument_spec: CommandArgumentSpec | None) -> str:
    if argument_spec is None:
        return _normalize_token(raw)
    return argument_spec.normalize_token(raw)


__all__ = [
    "CARDINAL_ALIASES",
    "CARDINAL_DELTAS",
    "CommandArgumentSpec",
    "CommandSpec",
    "export_command_manifest",
    "normalize_cardinal_token",
    "normalize_command_token",
    "parse_command",
]
