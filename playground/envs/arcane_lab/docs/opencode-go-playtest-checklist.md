# OpenCode Go Playtest Checklist

Purpose: track OpenCode Go model candidates for Arcane Lab official server-backed playtests.

## Setup Checks

- [x] Upgrade OpenCode to `1.14.25`.
- [x] Confirm `opencode-go` provider lists models.
- [x] Confirm OpenCode Go credential can issue requests with `opencode-go/deepseek-v4-flash`.

## Official Random-Crit Playtests

Use isolated workspaces under `agent_workspaces\opencode_runs\`, one server auth token per official attempt, and server-side verification only.

- [x] `opencode-go/deepseek-v4-pro` - success, official game `20260426_100955_3abfe03a`, reward `35975`, reached run 2 tick 7 with `echo_vault_attuned` and `echo_anchor`.
- [x] `opencode-go/kimi-k2.6` - failed, official game `20260426_103106_58d1a119`, reward `0`, stopped at run 1 tick 694; reached `quiet_archive` but did not retire or meet the prestige goals.
- [x] `opencode-go/qwen3.6-plus` - partial, official game `20260426_104820_ac5c2b68`, reward `9980`, reached run 2 with one retirement and insight `5`, but did not reach Echo Vault or craft `echo_anchor`. Run used OpenCode default variant; a first attempt failed on external-directory reads before the prompt was tightened.
- [x] `opencode-go/minimax-m2.7` - partial, official game `20260426_110054_b58d11b1`, reward `12635`, reached run 2 tick 225 with one retirement and insight `5`; server verification accepted, but no agent report was produced and Echo Vault / `echo_anchor` were not reached. Run used `--variant high`; prompt was delivered inline after this runner change.
- [x] `opencode-go/glm-5.1` - failed, official game `20260426_113337_0109bc77`, reward `0`, server verification rejected because tick budget `260` was exceeded at run 2 tick `650`. It reached `astral_capstone`, cleared Astral Foundry once, and completed 11 storylines, but retired with only insight `9`, so `echoed_foundation` / Echo Vault remained locked and `echo_anchor` was not crafted. Run used inline prompt + `--variant high`; an earlier runner crash left an orphan attempt that was stopped.
- [x] `opencode-go/mimo-v2.5-pro` - partial, official game `20260426_114540_ca1db2f9`, reward `17580`, server verification accepted at run 2 tick `0` with one retirement and insight `11`; it did not complete `echo_vault_attuned`, unlock Echo Vault, craft `echo_anchor`, or reach the insight `12` target. Run used inline prompt + `--variant high`; it retired just after the prompt's soft stop at run 1 tick `248`.

## Budgeted Prestige Track Spot Checks

Use `-Track budgeted-prestige`, inline prompt delivery, `--variant high`, server random crit mode, and a token-enforced lifetime tick budget of `260`.

- [x] `opencode-go/mimo-v2.5-pro` - success, official game `20260426_130019_8904d963`, reward `33035`, lifetime tick `222/260`, run 2 tick `6`, completed `echo_vault_attuned`, cleared Echo Vault, crafted `echo_anchor`, and verified with trajectory hash `cf568a55d169fff075eabef5facc7b2500a6fac7f8091ff4bd8db71368b85383`. Caveat: the model read server implementation details and placed an auth token in shell commands/logs while debugging token use, so this run is a goal-completion success but a rule/safety-adherence failure.
- [x] `opencode-go/deepseek-v4-pro` - partial, official game `20260426_130506_69c11ac6`, reward `19000`, lifetime tick `235/260`, reached run 2 with one retirement and insight `12`, but did not complete `astral_capstone`, unlock Echo Vault, complete `echo_vault_attuned`, or craft `echo_anchor`; verification accepted the official game and recorded trajectory hash `475b5b88c843acf7def108658dfcbec5aecc0a7d065fdadd608da0f0397d15da`. It had 142 commands and 19 failed commands, mainly from low-mana batch casts, buff-duration mistakes, and late retirement after Living Conduit.

## Track Coverage Follow-Ups

- [ ] Run `pure-blind` on one strong and one weaker model to separate true discovery from docs-assisted discovery.
- [ ] Run `mechanics-check` on at least two models to isolate SDK shape, batch command, buff duration, automation, random crit, and soft-stop discipline from long-route planning.
- [ ] Review `.runner\summary.json` `source_policy` and `softStopScore` alongside official reward for every new track run.

## Baseline / Prior Runs

- [x] `deepseek/deepseek-v4-pro` through OpenCode direct DeepSeek provider: early failure, official game `20260426_095207_0d7bfd13`, reward `3040`, no prestige goals achieved.
- [x] `opencode-go/deepseek-v4-flash` smoke only: returned `ok`; not a game playtest.
