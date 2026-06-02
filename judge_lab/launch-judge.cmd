@echo off
setlocal

set "WORKSPACE=E:\agent_misc\judge_lab"
set "BUNDLE=E:\agent_misc\benchmarks\results\20260324T_mail4agent_rust_admin_mailbox_access_judge_packets"
set "PROMPT_FILE=%WORKSPACE%\judge_prompt_current_bundle.txt"
set "LAST_MESSAGE=%WORKSPACE%\last_judge_message.txt"
set "CODEX_HOME=%WORKSPACE%\.codex_home"
set "SOURCE_CODEX_HOME=%USERPROFILE%\.codex"

if not exist "%CODEX_HOME%" mkdir "%CODEX_HOME%"
for %%F in (auth.json config.toml cap_sid version.json) do (
  if not exist "%CODEX_HOME%\%%F" if exist "%SOURCE_CODEX_HOME%\%%F" copy /Y "%SOURCE_CODEX_HOME%\%%F" "%CODEX_HOME%\%%F" >nul
)

if not exist "%PROMPT_FILE%" (
  echo Missing prompt file: %PROMPT_FILE%
  exit /b 1
)

if not exist "%BUNDLE%\score_sheet.csv" (
  echo Missing score sheet in bundle: %BUNDLE%
  exit /b 1
)

type "%PROMPT_FILE%" | codex exec -C "%WORKSPACE%" --skip-git-repo-check --full-auto --sandbox workspace-write --add-dir "%BUNDLE%" - -o "%LAST_MESSAGE%"
set "CODE=%ERRORLEVEL%"

echo.
echo Last judge message: %LAST_MESSAGE%
exit /b %CODE%
