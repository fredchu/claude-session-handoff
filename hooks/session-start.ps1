# Session Handoff - SessionStart hook
# Reads Markdown handoff shards and writes session context to stdout.

# ---- Configuration ----
$AgentId = "Main"
$HandoffRoot = Join-Path $env:USERPROFILE ".agents/handoff"
$Cli = Join-Path $env:USERPROFILE ".claude/skills/session-handoff/scripts/handoff_cli.py"
$LogDir = Join-Path $env:USERPROFILE ".claude/scripts"
$LogFile = Join-Path $LogDir "handoff-fetch.log"
# -----------------------

if (-not (Test-Path -LiteralPath $Cli -PathType Leaf)) {
    Write-Output "INFO: handoff_cli.py not found ($Cli) - is the session-handoff skill installed?"
    exit 0
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$env:PYTHONUTF8 = "1"

$pythonExe = $null
$pythonArgs = @()

# Qualify each candidate (probe success AND version >= 3.9) before selecting,
# so an outdated "py -3" does not shadow a supported "python" on PATH.
$candidates = @(
    @{ Exe = "py"; Args = @("-3") },
    @{ Exe = "python"; Args = @() }
)

foreach ($candidate in $candidates) {
    $candidateArgs = $candidate.Args
    $versionText = $null
    try {
        $versionText = (& $candidate.Exe @candidateArgs --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { continue }
    } catch {
        continue
    }
    if ($versionText -notmatch "Python\s+(\d+)\.(\d+)\.(\d+)") { continue }
    $candidateVersion = [version]::new(
        [int]$Matches[1],
        [int]$Matches[2],
        [int]$Matches[3]
    )
    if ($candidateVersion -lt [version]"3.9.0") { continue }
    $pythonExe = $candidate.Exe
    $pythonArgs = $candidateArgs
    break
}

if ($null -eq $pythonExe) {
    Write-Output "INFO: no suitable Python found (need 3.9+); handoff skipped."
    exit 0
}

& $pythonExe @pythonArgs $Cli session-start --root $HandoffRoot --agent $AgentId --active-budget 1500 --shared-budget 1000 2>>$LogFile
exit $LASTEXITCODE
