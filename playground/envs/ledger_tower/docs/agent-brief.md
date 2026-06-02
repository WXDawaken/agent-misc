# Ledger Tower Agent Brief

You are playing Ledger Tower, a deterministic fixed-value tower puzzle RPG.

Your job is to plan a route through six small floors. Keep a precise ledger:

- HP
- attack
- defense
- gold
- yellow and blue keys
- current position
- doors already opened
- monsters already defeated

Use `preview` before fights. Combat is deterministic and the player hits first.
If a fight would drop HP to `0` or less, the engine rejects it without spending
a move.

Shops sell:

- `attack`: +4 attack for 12 gold
- `defense`: +3 defense for 12 gold
- `hp`: +100 HP for 10 gold

Purchases matter. Buying the wrong stat can leave you short for later enemies
or the final boss.

Recommended workflow:

1. Read `docs/sdk-api.md` and `docs/tasks.md` if the track permits them.
2. Use direct `LedgerTowerSDK` practice only when the track says whitebox
   practice is available.
3. If the track provides a practice server token, use
   `LedgerTowerServerSDK(..., token_role="practice")` for only the advertised
   number of non-official practice games.
4. Build a compact route file under `logs\` from the information the track
   permits.
5. Use the official `LedgerTowerServerSDK` for the tracked attempt(s).
6. Call `verify()` on each official game you want scored. When a track permits
   multiple official attempts, the runner takes the best verified reward.
7. Treat `verify()` as final submission for that official game. After it, start
   a new official game for any remaining attempt; do not continue the submitted
   game.
