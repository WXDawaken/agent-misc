from __future__ import annotations

import sys
from pathlib import Path


_ENV_ROOT = Path(__file__).resolve().parent / "envs" / "arcane_lab"
if str(_ENV_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENV_ROOT))

from envs.arcane_lab import mcp_server as _mcp_server  # noqa: E402

for _name in dir(_mcp_server):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_mcp_server, _name)


if __name__ == "__main__":
    raise SystemExit(_mcp_server.main())

