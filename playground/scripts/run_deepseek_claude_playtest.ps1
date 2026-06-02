param(
    [ValidateSet("deepseek-v4-pro", "deepseek-v4-pro[1m]", "deepseek-v4-flash")]
    [string]$Model = "deepseek-v4-pro[1m]",
    [ValidateSet("low", "medium", "high", "xhigh", "max")]
    [string]$Effort = "high",
    [switch]$TrackMode,
    [string]$TrackConfigPath = "envs\arcane_lab\docs\tracks\config.json",
    [string]$Track = "budgeted-prestige",
    [string]$SharedPromptPath = "",
    [string]$PromptPath = "",
    [string]$OutDir = "agent_workspaces\deepseek_runs",
    [int]$TickBudget = 260,
    [int]$TimeoutMinutes = 240,
    [int]$StopAfterReportSeconds = 120,
    [string]$KeyPath = (Join-Path $env:USERPROFILE ".ds\ak"),
    [switch]$VerboseOutput,
    [switch]$StreamJson,
    [switch]$PartialMessages,
    [switch]$IncludeHookEvents,
    [switch]$PrepareOnly
)

$ErrorActionPreference = "Stop"

$claudeCommand = Get-Command claude.cmd -ErrorAction SilentlyContinue
if (-not $claudeCommand) {
    $claudeCommand = Get-Command claude -ErrorAction SilentlyContinue
}
if (-not $claudeCommand) {
    throw "Claude Code CLI not found on PATH."
}

if (-not $env:DEEPSEEK_API_KEY -and -not $env:ANTHROPIC_AUTH_TOKEN -and (Test-Path -LiteralPath $KeyPath)) {
    $key = Get-Content -LiteralPath $KeyPath | Where-Object { $_.Trim() } | Select-Object -First 1
    if ($key) {
        $env:DEEPSEEK_API_KEY = $key.Trim().Trim([char]0xFEFF).Trim('"').Trim("'")
    }
}

if (-not $env:DEEPSEEK_API_KEY -and -not $env:ANTHROPIC_AUTH_TOKEN) {
    throw "Set DEEPSEEK_API_KEY, ANTHROPIC_AUTH_TOKEN, or provide -KeyPath before running this script."
}

$requestedModel = $Model
$claudeModel = if ($Model -eq "deepseek-v4-pro") { "deepseek-v4-pro[1m]" } else { $Model }
$smallFastModel = "deepseek-v4-flash"

$sourceRoot = (Resolve-Path -LiteralPath ".").Path
$prepareScript = Join-Path $sourceRoot "scripts\prepare_agent_run.py"

if ($TrackMode) {
    if (-not $StreamJson) {
        $StreamJson = $true
    }
    if (-not $VerboseOutput) {
        $VerboseOutput = $true
    }
    $prepareArgs = @(
        "track",
        "--runner", "claude-code-deepseek",
        "--runner-client", "Claude Code DeepSeek",
        "--model", $claudeModel,
        "--reasoning-variant", $Effort,
        "--track", $Track,
        "--track-config-path", $TrackConfigPath,
        "--out-dir", $OutDir,
        "--server-url", "http://127.0.0.1:8765",
        "--label-prefix", "claude-code-deepseek",
        "--report-name-template", "claude_code_deepseek_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
    )
    if ($SharedPromptPath) {
        $prepareArgs += @("--shared-prompt-path", $SharedPromptPath)
    }
    if ($PromptPath) {
        $prepareArgs += @("--prompt-path", $PromptPath)
    }
    if ($PSBoundParameters.ContainsKey("TickBudget")) {
        $prepareArgs += @("--tick-budget", [string]$TickBudget)
    }
}
else {
    if (-not $PromptPath) {
        $PromptPath = "envs\arcane_lab\docs\deepseek-prestige-playtest-prompt.md"
    }
    if (-not (Test-Path -LiteralPath $PromptPath)) {
        throw "Prompt file not found: $PromptPath"
    }
    $workspaceSetupProfile = if ((Split-Path -Leaf $PromptPath) -like "*random*") { "deepseek-random" } else { "deepseek-prestige" }
    $prepareArgs = @(
        "prompt",
        "--runner", "claude-code-deepseek",
        "--model", $claudeModel,
        "--effort", $Effort,
        "--prompt-path", $PromptPath,
        "--out-dir", $OutDir,
        "--workspace-profile", $workspaceSetupProfile
    )
}

$prepareOutput = & python $prepareScript @prepareArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Runner preparation failed: $($prepareOutput | Out-String)"
}
$prepared = ($prepareOutput | Out-String) | ConvertFrom-Json -ErrorAction Stop
$workspaceDir = [string]$prepared.run_dir
$workspaceLogDir = [string]$prepared.logs_dir
$runnerDir = [string]$prepared.runner_dir
$metadataPath = [string]$prepared.metadata
$prompt = [string]$prepared.prompt

$outputExtension = if ($StreamJson) { "jsonl" } else { "txt" }
$outPath = Join-Path $runnerDir "claude_output.${outputExtension}"
$errPath = Join-Path $runnerDir "claude_error.log"
$promptInputPath = Join-Path $runnerDir "prompt.input.md"

$env:ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"
if (-not $env:ANTHROPIC_AUTH_TOKEN) {
    $env:ANTHROPIC_AUTH_TOKEN = $env:DEEPSEEK_API_KEY
}
$env:ANTHROPIC_MODEL = $claudeModel
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = $claudeModel
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = $claudeModel
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = $smallFastModel
$env:ANTHROPIC_SMALL_FAST_MODEL = $smallFastModel
$env:CLAUDE_CODE_SUBAGENT_MODEL = $smallFastModel
$env:CLAUDE_CODE_DISABLE_1M_CONTEXT = $null
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK = "1"
$env:CLAUDE_CODE_EFFORT_LEVEL = $Effort

$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json -ErrorAction Stop
$metadata | Add-Member -NotePropertyName "requested_model" -NotePropertyValue $requestedModel -Force
$metadata | Add-Member -NotePropertyName "claude_model" -NotePropertyValue $claudeModel -Force
$metadata | Add-Member -NotePropertyName "small_fast_model" -NotePropertyValue $smallFastModel -Force
$metadata | Add-Member -NotePropertyName "output" -NotePropertyValue $outPath -Force
$metadata | Add-Member -NotePropertyName "error_log" -NotePropertyValue $errPath -Force
$metadata | Add-Member -NotePropertyName "prompt_input" -NotePropertyValue $promptInputPath -Force
$metadata | Add-Member -NotePropertyName "stream_json" -NotePropertyValue ([bool]$StreamJson) -Force
$metadata | Add-Member -NotePropertyName "verbose_output" -NotePropertyValue ([bool]$VerboseOutput) -Force
$metadata | Add-Member -NotePropertyName "partial_messages" -NotePropertyValue ([bool]$PartialMessages) -Force
$metadata | Add-Member -NotePropertyName "include_hook_events" -NotePropertyValue ([bool]$IncludeHookEvents) -Force
$metadata | Add-Member -NotePropertyName "timeout_minutes" -NotePropertyValue $TimeoutMinutes -Force
$metadata | Add-Member -NotePropertyName "prompt_delivery" -NotePropertyValue "stdin_redirect" -Force
$metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

$taskPrompt = if ($TrackMode) {
@"
The complete playtest prompt is included below. Do not search for a prompt file;
use the instructions in this message as the authoritative task.
Do not inspect, print, manually set, or store runner auth environment variables;
the SDK reads them automatically.

$prompt
"@
}
else {
    $prompt
}
$taskPrompt | Set-Content -LiteralPath $promptInputPath -Encoding UTF8

$claudeArgs = @(
    "-p",
    "--model", $claudeModel,
    "--effort", $Effort,
    "--permission-mode", $(if ($TrackMode) { "bypassPermissions" } else { "acceptEdits" }),
    "--allowedTools", "Bash(python *),Bash(Get-Content *),Bash(Get-ChildItem *),Bash(Select-String *),Bash(New-Item *),Bash(Set-Content *),Read,Write,Edit,MultiEdit",
    "--disallowedTools", "NotebookEdit,WebFetch,WebSearch",
    "--no-session-persistence"
)

if ($VerboseOutput) {
    $claudeArgs += "--verbose"
}
if ($StreamJson) {
    $claudeArgs += @("--output-format", "stream-json")
}
if ($PartialMessages) {
    $claudeArgs += "--include-partial-messages"
}
if ($IncludeHookEvents) {
    $claudeArgs += "--include-hook-events"
}

if ($PrepareOnly) {
    Write-Host "Prepared isolated workspace: $workspaceDir"
    Write-Host "Runner output directory: $runnerDir"
    exit 0
}

$launchFile = $claudeCommand.Source
$launchArgs = $claudeArgs
$launchSuffix = [System.IO.Path]::GetExtension($launchFile)
if ($launchSuffix -in @(".cmd", ".bat")) {
    $cmd = Get-Command cmd.exe -ErrorAction Stop
    $launchArgs = @("/c", $launchFile) + $claudeArgs
    $launchFile = $cmd.Source
}
elseif ($launchFile.EndsWith(".ps1", [System.StringComparison]::OrdinalIgnoreCase)) {
    $pwsh = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if (-not $pwsh) {
        $pwsh = Get-Command powershell.exe -ErrorAction Stop
    }
    $launchArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $launchFile) + $claudeArgs
    $launchFile = $pwsh.Source
}

function Get-EnvValue {
    param([string]$Name)
    if (-not $Name) {
        return $null
    }
    $item = Get-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
    if ($item) {
        return $item.Value
    }
    return $null
}

function Set-EnvValue {
    param(
        [string]$Name,
        [AllowNull()][object]$Value
    )
    if (-not $Name) {
        return
    }
    if ($null -eq $Value -or [string]$Value -eq "") {
        Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
    }
    else {
        Set-Item -LiteralPath "Env:$Name" -Value ([string]$Value)
    }
}

Write-Host "RUN_DIR=$workspaceDir"
Write-Host "OUT_PATH=$outPath"

$serverUrlEnv = if ($prepared.server_url_env) { [string]$prepared.server_url_env } else { "ARCANE_LAB_SERVER_URL" }
$authTokenEnv = if ($prepared.auth_token_env) { [string]$prepared.auth_token_env } else { "ARCANE_LAB_AUTH_TOKEN" }
$practiceAuthTokenEnv = if ($prepared.practice_auth_token_env) { [string]$prepared.practice_auth_token_env } else { "" }
$dataPathEnv = if ($prepared.data_path_env) { [string]$prepared.data_path_env } else { "" }
$trackEnvNames = @(
    $serverUrlEnv,
    $authTokenEnv,
    $practiceAuthTokenEnv,
    $dataPathEnv,
    "ARCANE_LAB_CRIT_MODE",
    "ARCANE_LAB_CRIT_CHARGE_BONUS",
    "ARCANE_LAB_CRIT_RANDOM_CHANCE",
    "ARCANE_LAB_CRIT_RANDOM_BONUS"
) | Where-Object { $_ } | Select-Object -Unique
$oldTrackEnv = @{}
foreach ($envName in $trackEnvNames) {
    $oldTrackEnv[$envName] = Get-EnvValue -Name $envName
}
if ($TrackMode) {
    Set-EnvValue -Name $serverUrlEnv -Value $prepared.server_url
    Set-EnvValue -Name $authTokenEnv -Value $prepared.auth_token
    Set-EnvValue -Name $practiceAuthTokenEnv -Value $prepared.practice_auth_token
    Set-EnvValue -Name $dataPathEnv -Value $prepared.workspace_data_path
    Set-EnvValue -Name "ARCANE_LAB_CRIT_MODE" -Value ($prepared.token_crit_mode ?? "random")
    Set-EnvValue -Name "ARCANE_LAB_CRIT_CHARGE_BONUS" -Value $prepared.token_crit_charge_bonus
    Set-EnvValue -Name "ARCANE_LAB_CRIT_RANDOM_CHANCE" -Value $prepared.token_crit_random_chance
    Set-EnvValue -Name "ARCANE_LAB_CRIT_RANDOM_BONUS" -Value $prepared.token_crit_random_bonus
}

try {
    $process = Start-Process -FilePath $launchFile -ArgumentList $launchArgs -WorkingDirectory $workspaceDir -RedirectStandardInput $promptInputPath -RedirectStandardOutput $outPath -RedirectStandardError $errPath -WindowStyle Hidden -PassThru
}
finally {
    if ($TrackMode) {
        foreach ($envName in $oldTrackEnv.Keys) {
            Set-EnvValue -Name $envName -Value $oldTrackEnv[$envName]
        }
    }
}

$script:latestReport = $null
$script:reportFirstSeenAt = $null
$script:stoppedReason = $null
$startedAt = Get-Date

try {
    while (-not $process.HasExited) {
        $reports = Get-ChildItem -LiteralPath $workspaceLogDir -Filter "*.md" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending
        if ($reports) {
            if (-not $script:latestReport) {
                $script:latestReport = $reports[0].FullName
                $script:reportFirstSeenAt = Get-Date
            }
            elseif ($reports[0].FullName -ne $script:latestReport) {
                $script:latestReport = $reports[0].FullName
                $script:reportFirstSeenAt = Get-Date
            }
            elseif ($StopAfterReportSeconds -gt 0 -and ((Get-Date) - $script:reportFirstSeenAt).TotalSeconds -ge $StopAfterReportSeconds) {
                $script:stoppedReason = "stopped_after_report"
                Stop-Process -Id $process.Id -Force
                break
            }
        }

        if (((Get-Date) - $startedAt).TotalMinutes -ge $TimeoutMinutes) {
            $script:stoppedReason = "timeout"
            Stop-Process -Id $process.Id -Force
            break
        }
        Start-Sleep -Seconds 5
    }
}
finally {
    $process.Refresh()
}

if (-not $script:latestReport) {
    $reports = Get-ChildItem -LiteralPath $workspaceLogDir -Filter "*.md" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if ($reports) {
        $script:latestReport = $reports[0].FullName
    }
}

$exitCode = $null
try {
    if (-not $process.HasExited) {
        $process.WaitForExit(15000) | Out-Null
    }
    $exitCode = $process.ExitCode
}
catch {
    $exitCode = $null
}

if ($TrackMode) {
    $collectScript = Join-Path $sourceRoot "scripts\collect_track_summary.py"
    $collectArgs = @(
        $collectScript,
        "--source-root", $sourceRoot,
        "--metadata", $metadataPath,
        "--output", $outPath
    )
    if ($script:latestReport) {
        $collectArgs += @("--report", $script:latestReport)
    }
    if ($script:stoppedReason) {
        $collectArgs += @("--stopped-reason", $script:stoppedReason)
    }
    if ($null -ne $exitCode) {
        $collectArgs += @("--exit-code", [string]$exitCode)
    }
    & python @collectArgs
}
else {
    Write-Host "Saved Claude output to $outPath"
    Write-Host "Isolated workspace: $workspaceDir"
}
