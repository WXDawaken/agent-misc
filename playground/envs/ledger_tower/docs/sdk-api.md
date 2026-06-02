# Ledger Tower SDK API

## Direct Practice

```python
from sdk import LedgerTowerSDK

tower = LedgerTowerSDK(new=True)
obs = tower.observe()
result = tower.step("move east")
score = tower.score({"floor": "f3"})
tower.export_tracking("logs/practice_tracking.json")
```

Useful methods:

- `step(command: str) -> StepResult`
- `run(commands: list[str]) -> list[StepResult]`
- `run_script(path) -> list[StepResult]`
- `observe(include_text=True) -> dict`
- `list_available(kind: str) -> str`
- `score(goal: dict | None = None) -> dict`
- `metrics() -> dict`
- `export_tracking(path) -> Path`

## Official Server Play

Recommended final-submission path:

```powershell
python tools\ledger_submit_route.py --route logs\route.txt
```

Write one movement or buy command per line in `logs\route.txt`. The helper
creates one official game, executes the route, calls `verify()`, exports
tracking, and writes the required report. This avoids spending official attempts
while debugging reconnect or verification scripts. Commands that do not spend a
move are recorded as failed/non-moving commands, but the helper continues replay
by default and stops only after too many consecutive non-moving commands. Use
`--strict-invalid-stop` only when you want the legacy one-failed-command stop.

Manual SDK control is also available:

```python
from sdk import LedgerTowerServerSDK

tower = LedgerTowerServerSDK(new=True, label="my-run")
tower.run(["status", "map"])
verification = tower.verify()
```

The server SDK reads the official server URL and token from environment values
provided by the runner. Do not inspect, print, copy, or manually set those
values.

Some tracks provide a separate non-official server practice token instead of
the direct local engine. For those tracks, create practice games with:

```python
practice = LedgerTowerServerSDK(new=True, label="practice", token_role="practice")
```

Practice-token games cannot be verified and do not count toward official score.
For tracks that permit multiple official attempts, verify each official game you
want scored; the runner summary uses the best verified official reward for the
same task.

`verify()` submits the official game and closes it to further commands. If a
track permits more than one official attempt, create a fresh
`LedgerTowerServerSDK(new=True, ...)` game after each submission.
Official attempt limits count `new=True` official game creation, not currently
open games. Calling `verify()` never refunds or frees an official attempt.

Useful methods:

- `step(command: str) -> StepResult`
- `run(commands: list[str]) -> list[StepResult]`
- `observe(include_text=True) -> dict`
- `list_available(kind: str) -> str`
- `score(goal: dict | None = None) -> dict`
- `verify(goal: dict | None = None, tick_budget: int | None = None) -> dict`
- `trajectory() -> dict`
- `auth_status() -> dict`
- `export_tracking(path) -> Path`

## Observation Fields

Important fields:

- `obs["moves"]`
- `obs["floor"]`
- `obs["position"]`
- `obs["state"]["hp"]`
- `obs["state"]["atk"]`
- `obs["state"]["def"]`
- `obs["state"]["gold"]`
- `obs["state"]["keys"]`
- `obs["floor_map"]`
- `obs["floor_entities"]`
- `obs["known_enemies"]`
- `obs["score"]`
