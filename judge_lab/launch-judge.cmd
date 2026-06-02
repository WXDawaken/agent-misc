@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "WORKSPACE=%SCRIPT_DIR%"
set "BUNDLE=%JUDGE_BUNDLE%"
set "PROMPT_FILE="
set "LAST_MESSAGE="
set "CODEX_HOME="
set "SOURCE_CODEX_HOME=%USERPROFILE%\.codex"

:parse_args
if "%~1"=="" goto after_args
if /I "%~1"=="--help" goto usage_ok
if /I "%~1"=="-h" goto usage_ok
if /I "%~1"=="--bundle" goto set_bundle
if /I "%~1"=="--workspace" goto set_workspace
if /I "%~1"=="--prompt-file" goto set_prompt_file
if /I "%~1"=="--last-message" goto set_last_message
if /I "%~1"=="--codex-home" goto set_codex_home
if /I "%~1"=="--source-codex-home" goto set_source_codex_home
if "%BUNDLE%"=="" (
  set "BUNDLE=%~1"
  shift
  goto parse_args
)
echo Unknown argument: %~1
goto usage_fail

:set_bundle
if "%~2"=="" goto missing_value
set "BUNDLE=%~2"
shift
shift
goto parse_args

:set_workspace
if "%~2"=="" goto missing_value
set "WORKSPACE=%~2"
shift
shift
goto parse_args

:set_prompt_file
if "%~2"=="" goto missing_value
set "PROMPT_FILE=%~2"
shift
shift
goto parse_args

:set_last_message
if "%~2"=="" goto missing_value
set "LAST_MESSAGE=%~2"
shift
shift
goto parse_args

:set_codex_home
if "%~2"=="" goto missing_value
set "CODEX_HOME=%~2"
shift
shift
goto parse_args

:set_source_codex_home
if "%~2"=="" goto missing_value
set "SOURCE_CODEX_HOME=%~2"
shift
shift
goto parse_args

:after_args
if "%BUNDLE%"=="" (
  echo Missing packet bundle.
  goto usage_fail
)

if "%PROMPT_FILE%"=="" set "PROMPT_FILE=%WORKSPACE%\judge_prompt_current_bundle.txt"
if "%LAST_MESSAGE%"=="" set "LAST_MESSAGE=%WORKSPACE%\last_judge_message.txt"
if "%CODEX_HOME%"=="" set "CODEX_HOME=%WORKSPACE%\.codex_home"

if not exist "%WORKSPACE%\" (
  echo Missing workspace directory: %WORKSPACE%
  exit /b 1
)

if not exist "%BUNDLE%\" (
  echo Missing packet bundle directory: %BUNDLE%
  exit /b 1
)

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

echo Judge workspace: %WORKSPACE%
echo Packet bundle: %BUNDLE%
echo Prompt file: %PROMPT_FILE%
echo Last message: %LAST_MESSAGE%
echo Codex home: %CODEX_HOME%
echo.

type "%PROMPT_FILE%" | codex exec -C "%WORKSPACE%" --skip-git-repo-check --full-auto --sandbox workspace-write --add-dir "%BUNDLE%" - -o "%LAST_MESSAGE%"
set "CODE=%ERRORLEVEL%"

echo.
echo Last judge message: %LAST_MESSAGE%
exit /b %CODE%

:missing_value
echo Missing value for argument: %~1
goto usage_fail

:usage_ok
call :usage
exit /b 0

:usage_fail
call :usage
exit /b 1

:usage
echo Usage:
echo   %~nx0 --bundle ^<packet-bundle-dir^> [options]
echo   %~nx0 ^<packet-bundle-dir^> [options]
echo.
echo Options:
echo   --workspace ^<dir^>            Judge workspace. Defaults to this script directory.
echo   --prompt-file ^<path^>         Prompt file. Defaults to ^<workspace^>\judge_prompt_current_bundle.txt.
echo   --last-message ^<path^>        Output message path. Defaults to ^<workspace^>\last_judge_message.txt.
echo   --codex-home ^<dir^>           Isolated Codex home. Defaults to ^<workspace^>\.codex_home.
echo   --source-codex-home ^<dir^>    Source Codex home for auth/config copy. Defaults to %%USERPROFILE%%\.codex.
echo   --help                         Show this help.
echo.
echo Environment:
echo   JUDGE_BUNDLE can provide the packet bundle when --bundle is omitted.
exit /b 0
