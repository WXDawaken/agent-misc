# Ledger Tower

Ledger Tower is a deterministic fixed-value tower puzzle RPG for the
`playground` benchmark host. It is original content inspired only by the broad
genre shape of fixed-value tower puzzle RPGs: grid floors, keys, doors, shops,
finite monsters, visible combat arithmetic, and route-sensitive resource
management.

## Core Loop

- Move on a 9x9 floor grid.
- Collect stat gems, potions, keys, and the final `ledger_core`.
- Open colored doors with matching keys.
- Fight deterministic monsters only when the preview says you survive.
- Spend gold at shops for attack, defense, or HP.
- Exit the final floor after collecting the `ledger_core`.

Inspection commands are free. Movement, doors, fights, item pickups, stairs,
exits, and shop purchases spend `moves`, which is the official budget metric.

## Commands

- `status`
- `map [floor|all]`
- `list commands|enemies|items|shops|floors|goals|reference`
- `preview <direction|enemy_id|x y>`
- `move <north|east|south|west> [count]`
- `buy <attack|defense|hp> [count]`
- `save`
- `quit`

## Fight Formula

The player hits first.

```text
player_hit = max(0, player_atk - enemy_def)
rounds = ceil(enemy_hp / player_hit)
damage_taken = max(0, enemy_atk - player_def) * (rounds - 1)
```

A fight is rejected if `player_hit <= 0` or projected HP would be `0` or less.

## SDK

Direct practice:

```python
from sdk import LedgerTowerSDK

tower = LedgerTowerSDK(new=True)
tower.step("status")
```

Official server play:

```python
from sdk import LedgerTowerServerSDK

tower = LedgerTowerServerSDK(new=True)
tower.step("status")
verification = tower.verify()
```

The server SDK reads `LEDGER_TOWER_SERVER_URL` and `LEDGER_TOWER_AUTH_TOKEN`
from the runner environment automatically.
