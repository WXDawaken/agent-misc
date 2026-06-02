from __future__ import annotations

import sys
from pathlib import Path


_ENV_ROOT = Path(__file__).resolve().parents[1] / "envs" / "arcane_lab"
if str(_ENV_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENV_ROOT))

from envs.arcane_lab.sdk.arcane_lab_sdk import *  # noqa: F401,F403,E402

