[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$LauncherArgs
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "codex_multiagent_launcher.py"

if (-not (Test-Path $pythonScript)) {
    Write-Error "Python launcher not found: $pythonScript"
    exit 1
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -3 $pythonScript @LauncherArgs
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $pythonScript @LauncherArgs
    exit $LASTEXITCODE
}

Write-Error "Neither 'py' nor 'python' is available. Install Python 3.11+ to use this launcher."
exit 1
