# Salvage Run Mailbox Collaboration

## Intent

Define a mailbox-first collaboration split between the new `salvage_run` and `game_engine` projects.

## Roles

- `salvage_run_dev`
  - front door for gameplay and product requests
  - owns `salvage_run/`, `test/test_salvage_run.py`, and related game docs
- `game_engine_dev`
  - provides reusable engine primitives and contracts
  - owns `game_engine/`, `test/test_game_engine.py`, and engine-facing docs

## Boundary

- `salvage_run_dev` must not edit `game_engine/`
- `game_engine_dev` must not edit `salvage_run/`
- cross-project needs should be turned into mailbox requests instead of direct edits across ownership boundaries

## Routing Rule

- send end-user or coordinator requirements to `salvage_run_dev` first
- only send work to `game_engine_dev` when `salvage_run_dev` identifies a bounded missing engine capability

## Progress Tracking

- each on-call reply should include an explicit `task_status`
- use mailbox-native status updates instead of guessing completion from thread silence or unread counts
- treat `waiting_on_peer` as the normal state when one role has handed off bounded work to the other
- if a role receives only a terminal completion/deferred/cancelled notice after its own thread state is already terminal, it should absorb that delivery without sending another no-op completion reply

## Why This Helps

- it creates a real coordination seam instead of letting one agent silently edit both projects
- it gives A2A runs a clearer ownership model
- it keeps `game_engine` from growing through accidental convenience edits
