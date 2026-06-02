from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType


DEFAULT_ENV = "arcane_lab"
ENV_MODULES = {
    "arcane_lab": "envs.arcane_lab.server",
    "ledger_tower": "envs.ledger_tower.server",
}


def _env_root(env_id: str) -> Path:
    return Path(__file__).resolve().parent / "envs" / env_id


def _add_env_import_path(env_id: str) -> None:
    root = _env_root(env_id)
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def _load_env_server(env_id: str) -> ModuleType:
    try:
        module_name = ENV_MODULES[env_id]
    except KeyError as exc:
        known = ", ".join(sorted(ENV_MODULES))
        raise SystemExit(f"unknown environment {env_id!r}; known environments: {known}") from exc
    _add_env_import_path(env_id)
    return importlib.import_module(module_name)


def _parse_unified_args(argv: list[str]) -> tuple[str, list[str], bool]:
    env_id = DEFAULT_ENV
    env_args: list[str] = []
    list_envs = False
    mint_index = argv.index("mint-token") if "mint-token" in argv else len(argv)
    i = 0
    while i < len(argv):
        arg = argv[i]
        if i < mint_index and arg == "--list-envs":
            list_envs = True
            i += 1
            continue
        if i < mint_index and arg == "--env":
            if i + 1 >= len(argv):
                raise SystemExit("--env requires an environment id")
            env_id = argv[i + 1]
            i += 2
            continue
        if i < mint_index and arg.startswith("--env="):
            env_id = arg.split("=", 1)[1]
            i += 1
            continue
        env_args.append(arg)
        i += 1
    return env_id, env_args, list_envs


_default_server = _load_env_server(DEFAULT_ENV)

for _name in dir(_default_server):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_default_server, _name)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    env_id, env_args, list_envs = _parse_unified_args(args)
    if list_envs:
        print("\n".join(sorted(ENV_MODULES)))
        return 0
    return _load_env_server(env_id).main(env_args)


if __name__ == "__main__":
    raise SystemExit(main())
