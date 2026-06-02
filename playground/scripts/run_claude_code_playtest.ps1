param(
    [string]$Model = "opus",
    [ValidateSet("low", "medium", "high", "xhigh", "max")]
    [string]$Effort = "high",
    [string]$TrackConfigPath = "envs\arcane_lab\docs\tracks\config.json",
    [string]$Track = "budgeted-prestige",
    [string]$SharedPromptPath = "",
    [string]$PromptPath = "",
    [string]$OutDir = "agent_workspaces\claude_code_runs",
    [int]$TickBudget = 260,
    [int]$TimeoutMinutes = 240,
    [int]$StopAfterReportSeconds = 120,
    [string]$ApiKeyPath = "",
    [switch]$VerboseOutput,
    [switch]$StreamJson,
    [switch]$PartialMessages,
    [switch]$IncludeHookEvents,
    [switch]$Bare,
    [switch]$PreserveAnthropicEnv,
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

$sourceRoot = (Resolve-Path -LiteralPath ".").Path
$prepareScript = Join-Path $sourceRoot "scripts\prepare_agent_run.py"

if (-not $StreamJson) {
    $StreamJson = $true
}
if (-not $VerboseOutput) {
    $VerboseOutput = $true
}

$prepareArgs = @(
    "track",
    "--runner", "claude-code",
    "--runner-client", "Claude Code",
    "--model", $Model,
    "--reasoning-variant", $Effort,
    "--track", $Track,
    "--track-config-path", $TrackConfigPath,
    "--out-dir", $OutDir,
    "--server-url", "http://127.0.0.1:8765",
    "--label-prefix", "claude-code",
    "--report-name-template", "claude_code_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
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

$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json -ErrorAction Stop
$metadata | Add-Member -NotePropertyName "output" -NotePropertyValue $outPath -Force
$metadata | Add-Member -NotePropertyName "error_log" -NotePropertyValue $errPath -Force
$metadata | Add-Member -NotePropertyName "prompt_input" -NotePropertyValue $promptInputPath -Force
$metadata | Add-Member -NotePropertyName "stream_json" -NotePropertyValue ([bool]$StreamJson) -Force
$metadata | Add-Member -NotePropertyName "verbose_output" -NotePropertyValue ([bool]$VerboseOutput) -Force
$metadata | Add-Member -NotePropertyName "partial_messages" -NotePropertyValue ([bool]$PartialMessages) -Force
$metadata | Add-Member -NotePropertyName "include_hook_events" -NotePropertyValue ([bool]$IncludeHookEvents) -Force
$metadata | Add-Member -NotePropertyName "timeout_minutes" -NotePropertyValue $TimeoutMinutes -Force
$metadata | Add-Member -NotePropertyName "prompt_delivery" -NotePropertyValue "stdin_redirect" -Force
$metadata | Add-Member -NotePropertyName "claude_bare" -NotePropertyValue ([bool]$Bare) -Force
$metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

$taskPrompt = @"
The complete playtest prompt is included below. Do not search for a prompt file;
use the instructions in this message as the authoritative task.
Do not inspect, print, manually set, or store runner auth environment variables;
the SDK reads them automatically.

$prompt
"@
$taskPrompt | Set-Content -LiteralPath $promptInputPath -Encoding UTF8

$claudeArgs = @(
    "-p",
    "--model", $Model,
    "--effort", $Effort,
    "--permission-mode", "bypassPermissions",
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
if ($Bare) {
    $claudeArgs += "--bare"
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

Write-Host "RUN_DIR=$workspaceDir"
Write-Host "OUT_PATH=$outPath"

$oldServerUrl = $env:ARCANE_LAB_SERVER_URL
$oldToken = $env:ARCANE_LAB_AUTH_TOKEN
$oldCritMode = $env:ARCANE_LAB_CRIT_MODE
$oldCritChargeBonus = $env:ARCANE_LAB_CRIT_CHARGE_BONUS
$oldCritRandomChance = $env:ARCANE_LAB_CRIT_RANDOM_CHANCE
$oldCritRandomBonus = $env:ARCANE_LAB_CRIT_RANDOM_BONUS
$oldDisableTraffic = $env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC
$oldDisableFallback = $env:CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK
$oldEffort = $env:CLAUDE_CODE_EFFORT_LEVEL
$oldAnthropicApiKey = $env:ANTHROPIC_API_KEY
$oldAnthropicBaseUrl = $env:ANTHROPIC_BASE_URL
$oldAnthropicModel = $env:ANTHROPIC_MODEL
$oldAnthropicSmallFastModel = $env:ANTHROPIC_SMALL_FAST_MODEL

$env:ARCANE_LAB_SERVER_URL = [string]$prepared.server_url
$env:ARCANE_LAB_AUTH_TOKEN = [string]$prepared.auth_token
$env:ARCANE_LAB_CRIT_MODE = [string]($prepared.token_crit_mode ?? "random")
$env:ARCANE_LAB_CRIT_CHARGE_BONUS = if ($null -ne $prepared.token_crit_charge_bonus) { [string]$prepared.token_crit_charge_bonus } else { $null }
$env:ARCANE_LAB_CRIT_RANDOM_CHANCE = if ($null -ne $prepared.token_crit_random_chance) { [string]$prepared.token_crit_random_chance } else { $null }
$env:ARCANE_LAB_CRIT_RANDOM_BONUS = if ($null -ne $prepared.token_crit_random_bonus) { [string]$prepared.token_crit_random_bonus } else { $null }
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK = "1"
$env:CLAUDE_CODE_EFFORT_LEVEL = $Effort

if ($ApiKeyPath -and -not $env:ANTHROPIC_API_KEY -and (Test-Path -LiteralPath $ApiKeyPath)) {
    $key = Get-Content -LiteralPath $ApiKeyPath | Where-Object { $_.Trim() } | Select-Object -First 1
    if ($key) {
        $env:ANTHROPIC_API_KEY = $key.Trim().Trim([char]0xFEFF).Trim('"').Trim("'")
    }
}

if (-not $PreserveAnthropicEnv) {
    $env:ANTHROPIC_BASE_URL = $null
    $env:ANTHROPIC_MODEL = $null
    $env:ANTHROPIC_SMALL_FAST_MODEL = $null
}

try {
    $process = Start-Process -FilePath $launchFile -ArgumentList $launchArgs -WorkingDirectory $workspaceDir -RedirectStandardInput $promptInputPath -RedirectStandardOutput $outPath -RedirectStandardError $errPath -WindowStyle Hidden -PassThru
}
finally {
    $env:ARCANE_LAB_SERVER_URL = $oldServerUrl
    $env:ARCANE_LAB_AUTH_TOKEN = $oldToken
    $env:ARCANE_LAB_CRIT_MODE = $oldCritMode
    $env:ARCANE_LAB_CRIT_CHARGE_BONUS = $oldCritChargeBonus
    $env:ARCANE_LAB_CRIT_RANDOM_CHANCE = $oldCritRandomChance
    $env:ARCANE_LAB_CRIT_RANDOM_BONUS = $oldCritRandomBonus
    $env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = $oldDisableTraffic
    $env:CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK = $oldDisableFallback
    $env:CLAUDE_CODE_EFFORT_LEVEL = $oldEffort
    $env:ANTHROPIC_API_KEY = $oldAnthropicApiKey
    $env:ANTHROPIC_BASE_URL = $oldAnthropicBaseUrl
    $env:ANTHROPIC_MODEL = $oldAnthropicModel
    $env:ANTHROPIC_SMALL_FAST_MODEL = $oldAnthropicSmallFastModel
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
