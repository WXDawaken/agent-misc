param(
    [Parameter(Mandatory = $true)]
    [string]$Model,
    [string]$TrackConfigPath = "envs\arcane_lab\docs\tracks\config.json",
    [string]$SharedPromptPath = "",
    [string]$PromptPath = "",
    [string]$Track = "budgeted-prestige",
    [string]$OutDir = "agent_workspaces\opencode_runs",
    [int]$TickBudget = 260,
    [int]$TimeoutMinutes = 45,
    [int]$StopAfterReportSeconds = 45,
    [string]$ReasoningVariant = "high"
)

$ErrorActionPreference = "Stop"

$opencodeCommand = Get-Command opencode.cmd -ErrorAction SilentlyContinue
if (-not $opencodeCommand) {
    $opencodeCommand = Get-Command opencode -ErrorAction SilentlyContinue
}
if (-not $opencodeCommand) {
    throw "OpenCode CLI not found on PATH."
}

$sourceRoot = (Resolve-Path -LiteralPath ".").Path
$prepareScript = Join-Path $sourceRoot "scripts\prepare_agent_run.py"
$prepareArgs = @(
    "track",
    "--runner", "opencode-go",
    "--runner-client", "OpenCode Go",
    "--model", $Model,
    "--reasoning-variant", $ReasoningVariant,
    "--track", $Track,
    "--track-config-path", $TrackConfigPath,
    "--out-dir", $OutDir,
    "--server-url", "http://127.0.0.1:8765",
    "--label-prefix", "opencode-go",
    "--report-name-template", "opencode_go_random_playtest_{track}_{safe_model}_{timestamp}_report.md"
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

$runDir = [string]$prepared.run_dir
$runnerDir = [string]$prepared.runner_dir
$workspaceLogDir = [string]$prepared.logs_dir
$timestamp = [string]$prepared.timestamp
$safeModel = [string]$prepared.safe_model
$label = [string]$prepared.label
$taskId = [string]$prepared.task_id
$serverUrl = [string]$prepared.server_url
$TickBudget = [int]$prepared.tick_budget
$softStopTick = [int]$prepared.soft_stop_tick
$sourcePolicyExtraPatterns = @($prepared.source_policy_extra_forbidden)
$prompt = [string]$prepared.prompt

$metadataPath = [string]$prepared.metadata
$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json -ErrorAction Stop
$metadata | Add-Member -NotePropertyName "prompt_delivery" -NotePropertyValue "inline_message" -Force
$metadata | Add-Member -NotePropertyName "timeout_minutes" -NotePropertyValue $TimeoutMinutes -Force
$metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

$outPath = Join-Path $runnerDir "opencode_output.jsonl"
$errPath = Join-Path $runnerDir "opencode_error.log"
$summaryPath = Join-Path $runnerDir "summary.json"
$title = "arcane-lab-$label"

Write-Host "RUN_DIR=$runDir"
Write-Host "OUT_PATH=$outPath"

$message = @"
The complete playtest prompt is included below. Do not search for a prompt file;
use the instructions in this message as the authoritative task.
Do not inspect, print, manually set, or store runner auth environment variables;
the SDK reads them automatically.

$prompt
"@
$args = @(
    "run",
    "--dir", $runDir,
    "-m", $Model,
    "--variant", $ReasoningVariant,
    "--agent", "build",
    "--format", "json",
    "--title", $title,
    "--",
    $message
)

$script:latestReport = $null
$script:reportFirstSeenAt = $null
$script:stoppedReason = $null

function Quote-ProcessArgument([string]$Value) {
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

$wrapperDir = Split-Path -Parent $opencodeCommand.Source
$nodeScript = Join-Path $wrapperDir "node_modules\opencode-ai\bin\opencode"
if (Test-Path -LiteralPath $nodeScript) {
    $bundledNode = Join-Path $wrapperDir "node.exe"
    if (Test-Path -LiteralPath $bundledNode) {
        $launchFile = $bundledNode
    }
    else {
        $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
        if (-not $nodeCommand) {
            $nodeCommand = Get-Command node -ErrorAction Stop
        }
        $launchFile = $nodeCommand.Source
    }
    $launchArgs = @($nodeScript) + $args
}
else {
    $launchFile = $opencodeCommand.Source
    $launchArgs = $args
    if ($launchFile.EndsWith(".ps1", [System.StringComparison]::OrdinalIgnoreCase)) {
        $pwsh = Get-Command pwsh.exe -ErrorAction SilentlyContinue
        if (-not $pwsh) {
            $pwsh = Get-Command powershell.exe -ErrorAction Stop
        }
        $launchArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $launchFile) + $args
        $launchFile = $pwsh.Source
    }
}
$oldServerUrl = $env:ARCANE_LAB_SERVER_URL
$oldToken = $env:ARCANE_LAB_AUTH_TOKEN
$oldCritMode = $env:ARCANE_LAB_CRIT_MODE
$oldCritChargeBonus = $env:ARCANE_LAB_CRIT_CHARGE_BONUS
$oldCritRandomChance = $env:ARCANE_LAB_CRIT_RANDOM_CHANCE
$oldCritRandomBonus = $env:ARCANE_LAB_CRIT_RANDOM_BONUS
$env:ARCANE_LAB_SERVER_URL = $serverUrl
$env:ARCANE_LAB_AUTH_TOKEN = [string]$prepared.auth_token
$env:ARCANE_LAB_CRIT_MODE = [string]($prepared.token_crit_mode ?? "random")
$env:ARCANE_LAB_CRIT_CHARGE_BONUS = if ($null -ne $prepared.token_crit_charge_bonus) { [string]$prepared.token_crit_charge_bonus } else { $null }
$env:ARCANE_LAB_CRIT_RANDOM_CHANCE = if ($null -ne $prepared.token_crit_random_chance) { [string]$prepared.token_crit_random_chance } else { $null }
$env:ARCANE_LAB_CRIT_RANDOM_BONUS = if ($null -ne $prepared.token_crit_random_bonus) { [string]$prepared.token_crit_random_bonus } else { $null }

try {
    $launchArgumentText = ($launchArgs | ForEach-Object { Quote-ProcessArgument $_ }) -join " "
    $process = Start-Process -FilePath $launchFile -ArgumentList $launchArgumentText -WorkingDirectory $runDir -RedirectStandardOutput $outPath -RedirectStandardError $errPath -WindowStyle Hidden -PassThru
}
finally {
    $env:ARCANE_LAB_SERVER_URL = $oldServerUrl
    $env:ARCANE_LAB_AUTH_TOKEN = $oldToken
    $env:ARCANE_LAB_CRIT_MODE = $oldCritMode
    $env:ARCANE_LAB_CRIT_CHARGE_BONUS = $oldCritChargeBonus
    $env:ARCANE_LAB_CRIT_RANDOM_CHANCE = $oldCritRandomChance
    $env:ARCANE_LAB_CRIT_RANDOM_BONUS = $oldCritRandomBonus
}

try {
    while (-not $process.HasExited) {
        $reports = Get-ChildItem -LiteralPath $workspaceLogDir -Filter "opencode_go_random_playtest_*_report.md" -File -ErrorAction SilentlyContinue |
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

        if (((Get-Date) - [datetime]::ParseExact($timestamp, "yyyyMMdd_HHmmss", $null)).TotalMinutes -ge $TimeoutMinutes) {
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

$verification = $null
$verificationPath = $null
$serverGames = Join-Path $sourceRoot "logs\server\games"
if (Test-Path -LiteralPath $serverGames) {
    foreach ($file in Get-ChildItem -LiteralPath $serverGames -Recurse -Filter "verification.json" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending) {
        try {
            $candidate = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
            if ($candidate.task_id -eq $taskId) {
                $verification = $candidate
                $verificationPath = $file.FullName
                break
            }
        }
        catch {
            continue
        }
    }
}

if (-not $script:latestReport) {
    $reports = Get-ChildItem -LiteralPath $workspaceLogDir -Filter "opencode_go_random_playtest_*_report.md" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if ($reports) {
        $script:latestReport = $reports[0].FullName
    }
}

function Test-OutputAccessPolicy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputPath,
        [Parameter(Mandatory = $true)]
        [string]$Track,
        [object[]]$ExtraForbiddenPatterns = @()
    )

    $violations = @()
    if (-not (Test-Path -LiteralPath $OutputPath)) {
        return [ordered]@{
            violation_count = 0
            violations = @()
        }
    }

    $patterns = @(
        @{ Name = "data-file"; Pattern = "data\\arcane_lab.json"; Regex = '(^|[\\/"''\s])data[\\/]+arcane_lab\.json(["''\s]|$)' },
        @{ Name = "game-source"; Pattern = "game.py"; Regex = '(^|[\\/"''\s])game\.py(["''\s]|$)' },
        @{ Name = "server-source"; Pattern = "server.py"; Regex = '(^|[\\/"''\s])server\.py(["''\s]|$)' },
        @{ Name = "mcp-source"; Pattern = "mcp_server.py"; Regex = '(^|[\\/"''\s])mcp_server\.py(["''\s]|$)' },
        @{ Name = "sdk-source"; Pattern = "sdk\\arcane_lab_sdk.py"; Regex = '(^|[\\/"''\s])sdk[\\/]+arcane_lab_sdk\.py(["''\s]|$)' },
        @{ Name = "sdk-server-source"; Pattern = "sdk\\server_sdk.py"; Regex = '(^|[\\/"''\s])sdk[\\/]+server_sdk\.py(["''\s]|$)' },
        @{ Name = "sdk-init-source"; Pattern = "sdk\\__init__.py"; Regex = '(^|[\\/"''\s])sdk[\\/]+__init__\.py(["''\s]|$)' },
        @{ Name = "sdk-result-source"; Pattern = "sdk\\result.py"; Regex = '(^|[\\/"''\s])sdk[\\/]+result\.py(["''\s]|$)' },
        @{ Name = "sdk-glob"; Pattern = "sdk/**/*" },
        @{ Name = "script-smoke"; Pattern = "scripts\\smoke.txt"; Regex = '(^|[\\/"''\s])scripts[\\/]+smoke\.txt(["''\s]|$)' },
        @{ Name = "script-midgame"; Pattern = "scripts\\midgame_smoke.txt"; Regex = '(^|[\\/"''\s])scripts[\\/]+midgame_smoke\.txt(["''\s]|$)' },
        @{ Name = "script-late"; Pattern = "scripts\\late_playtest.txt"; Regex = '(^|[\\/"''\s])scripts[\\/]+late_playtest\.txt(["''\s]|$)' },
        @{ Name = "script-retire"; Pattern = "scripts\\retire_smoke.txt"; Regex = '(^|[\\/"''\s])scripts[\\/]+retire_smoke\.txt(["''\s]|$)' },
        @{ Name = "script-prestige"; Pattern = "scripts\\prestige_smoke.txt"; Regex = '(^|[\\/"''\s])scripts[\\/]+prestige_smoke\.txt(["''\s]|$)' },
        @{ Name = "debug-goals"; Pattern = "goals_debug" },
        @{ Name = "debug-goals-cli"; Pattern = "list goals debug" }
    )
    foreach ($extra in $ExtraForbiddenPatterns) {
        if (-not $extra) {
            continue
        }
        $entry = @{
            Name = [string]$extra.name
            Pattern = [string]$extra.pattern
        }
        if ($extra.regex) {
            $entry.Regex = [string]$extra.regex
        }
        if (-not $entry.Name -or -not $entry.Pattern) {
            continue
        }
        $patterns += $entry
    }

    $lineNumber = 0
    foreach ($raw in Get-Content -LiteralPath $OutputPath -ErrorAction SilentlyContinue) {
        $lineNumber += 1
        try {
            $event = $raw | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            continue
        }
        if ($event.type -ne "tool_use") {
            continue
        }
        $tool = [string]$event.part.tool
        if ($tool -in @("write", "edit", "todowrite")) {
            continue
        }
        $inputJson = ($event.part.state.input | ConvertTo-Json -Compress -Depth 12)
        foreach ($pattern in $patterns) {
            $matched = if ($pattern.ContainsKey("Regex")) {
                $inputJson -match $pattern.Regex
            }
            else {
                $inputJson.IndexOf($pattern.Pattern, [StringComparison]::OrdinalIgnoreCase) -ge 0
            }
            if ($matched) {
                $violations += [ordered]@{
                    line = $lineNumber
                    tool = $tool
                    name = $pattern.Name
                    pattern = $pattern.Pattern
                }
            }
        }
    }

    return [ordered]@{
        violation_count = $violations.Count
        violations = $violations
    }
}

$exitCode = $null
try {
    $exitCode = $process.ExitCode
}
catch {
    $exitCode = $null
}

$sourcePolicy = Test-OutputAccessPolicy -OutputPath $outPath -Track $Track -ExtraForbiddenPatterns $sourcePolicyExtraPatterns

function Test-GoalStatusAchieved {
    param($Status)
    if ($null -eq $Status) {
        return $false
    }
    if ($Status -is [bool]) {
        return [bool]$Status
    }
    if ($Status.PSObject.Properties.Name -contains "achieved") {
        return [bool]$Status.achieved
    }
    return [bool]$Status
}

function Get-GoalCompletion {
    param($Verification)
    if (-not $Verification) {
        return $null
    }
    if ($Verification.PSObject.Properties.Name -contains "goalCompletion" -and $Verification.goalCompletion) {
        return [ordered]@{
            achieved = $Verification.goalCompletion.achieved
            achieved_count = $Verification.goalCompletion.achievedCount
            total = $Verification.goalCompletion.total
            failed = @($Verification.goalCompletion.failed)
        }
    }
    $goal = $Verification.score.goal
    $failed = @()
    $total = 0
    if ($goal) {
        foreach ($property in $goal.PSObject.Properties) {
            $total += 1
            if (-not (Test-GoalStatusAchieved -Status $property.Value)) {
                $failed += $property.Name
            }
        }
    }
    $achieved = if ($total -eq 0) { $null } else { $failed.Count -eq 0 }
    return [ordered]@{
        achieved = $achieved
        achieved_count = $total - $failed.Count
        total = $total
        failed = $failed
    }
}

function Get-VerificationOutcome {
    param($Verification, $GoalCompletion)
    if (-not $Verification) {
        return $null
    }
    if ($Verification.PSObject.Properties.Name -contains "outcome" -and $Verification.outcome) {
        return $Verification.outcome
    }
    if (-not $Verification.accepted) {
        return "rejected"
    }
    if ($GoalCompletion -and $GoalCompletion.achieved -eq $false) {
        return "partial"
    }
    if ($GoalCompletion -and $GoalCompletion.achieved -eq $true) {
        return "success"
    }
    return "accepted"
}

$goalCompletion = Get-GoalCompletion -Verification $verification
$summary = [ordered]@{
    model = $Model
    track = $Track
    run_dir = $runDir
    output = $outPath
    error_log = $errPath
    report = $script:latestReport
    stopped_reason = $script:stoppedReason
    exit_code = $exitCode
    task_id = $taskId
    verification_path = $verificationPath
    game_id = if ($verification) { $verification.game_id } else { $null }
    reward = if ($verification) { $verification.reward } else { $null }
    accepted = if ($verification) { $verification.accepted } else { $null }
    outcome = Get-VerificationOutcome -Verification $verification -GoalCompletion $goalCompletion
    goal_achieved = if ($goalCompletion) { $goalCompletion.achieved } else { $null }
    goal_completion = $goalCompletion
    goal_failed = if ($goalCompletion) { @($goalCompletion.failed) } else { $null }
    tick = if ($verification) { $verification.final.tick } else { $null }
    lifetime_tick = if ($verification) { $verification.final.lifetime_tick } else { $null }
    soft_stop_tick = if ($verification) { $verification.softStopTick } else { $softStopTick }
    soft_stop_exceeded = if ($verification) { $verification.softStopExceeded } else { $null }
    soft_stop_score = if ($verification) { $verification.softStopScore } else { $null }
    compliance_score = if ($verification) { $verification.complianceScore } else { $null }
    source_policy = $sourcePolicy
    run = if ($verification) { $verification.final.run } else { $null }
    retirements = if ($verification) { $verification.final.retirements } else { $null }
    insight = if ($verification) { $verification.final.insight } else { $null }
    trajectory_hash = if ($verification) { $verification.trajectory_hash } else { $null }
}

$collectScript = Join-Path $sourceRoot "scripts\collect_track_summary.py"
if (Test-Path -LiteralPath $collectScript) {
    $collectArgs = @(
        "--source-root", $sourceRoot,
        "--metadata", $metadataPath,
        "--output", $outPath,
        "--summary-out", $summaryPath
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
    $collectOutput = & python $collectScript @collectArgs 2>&1
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $summaryPath)) {
        $collected = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json -ErrorAction Stop
        $collected | Add-Member -NotePropertyName "error_log" -NotePropertyValue $errPath -Force
        $collected | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
        $collected | ConvertTo-Json -Depth 8
        exit 0
    }
    Write-Warning "Common summary collection failed; falling back to local summary: $($collectOutput | Out-String)"
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8
