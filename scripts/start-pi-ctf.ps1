[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("web", "realtime-web-game", "pwn", "reverse", "crypto", "forensics", "malware", "misc", "orchestrator")]
    [string]$Category,

    [string]$Workspace = ".",
    [string]$Instruction = "",
    [string]$Provider = "openai-codex",
    [string]$Model = "",

    [ValidateSet("off", "minimal", "low", "medium", "high", "xhigh", "max")]
    [string]$Thinking = "medium",

    [ValidateSet("powershell", "bash")]
    [string]$Shell = "powershell",

    [switch]$Interactive,
    [switch]$KeepSession,
    [switch]$Login,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:\PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ResolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
$SkillFile = Join-Path $RepoRoot "skills\$Category\SKILL.md"
if (-not (Test-Path -LiteralPath $SkillFile -PathType Leaf)) {
    throw "CTF skill not found: $SkillFile"
}

$Pi = (Get-Command pi -ErrorAction Stop).Source
$PiCtfRoot = Join-Path $env:USERPROFILE ".pi\ctf-agent"
if (-not (Test-Path -LiteralPath (Join-Path $PiCtfRoot "settings.json"))) {
    throw "Pi CTF profile is missing. Run scripts\install-pi-ctf.ps1 first."
}

$ToolName = if ($Shell -eq "bash") { "bash" } else { "powershell" }
$ToolAllowlist = "read,$ToolName,edit,write"
$HypaPath = Join-Path $env:USERPROFILE ".local\bin\hypa.exe"
$HypaAvailable = [bool](Get-Command hypa -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath $HypaPath -PathType Leaf)
$HypaRule = if ($HypaAvailable) {
    "Use hypa only for large repetitive non-evidence output. Rerun a narrow direct command for every exact flag, credential, hash, address, offset, payload, or decisive error."
}
else {
    "Save large raw command output to the workspace before returning only the decisive lines."
}

if (-not $Instruction) {
    $Instruction = "Work only on the supplied authorized CTF task in this workspace. Read existing artifacts and notes first. $HypaRule Return exactly five lines: Status, Finding, Evidence, Candidate, Next."
}

$PiArguments = @(
    "--provider", $Provider,
    "--thinking", $Thinking,
    "--no-extensions",
    "--no-context-files",
    "--no-skills",
    "--no-prompt-templates",
    "--no-themes",
    "--no-approve",
    "--tools", $ToolAllowlist,
    "--skill", $SkillFile
)
if ($Model) {
    $PiArguments += @("--model", $Model)
}
if (-not $Interactive) {
    $PiArguments += "--print"
}
if (-not $KeepSession -and -not $Interactive) {
    $PiArguments += "--no-session"
}
$PiArguments += @("--", $Instruction)

if ($DryRun) {
    [pscustomobject]@{
        cwd = $ResolvedWorkspace
        agent_dir = $PiCtfRoot
        category = $Category
        skill = $SkillFile
        tools = $ToolAllowlist
        provider = $Provider
        model = $Model
        thinking = $Thinking
        ephemeral = (-not $KeepSession -and -not $Interactive)
        hypa_available = $HypaAvailable
        argv = $PiArguments
    } | ConvertTo-Json -Depth 4
    exit 0
}

$PreviousAgentDir = $env:PI_CODING_AGENT_DIR
$PreviousCacheRetention = $env:PI_CACHE_RETENTION
$PreviousSkipVersionCheck = $env:PI_SKIP_VERSION_CHECK
$PreviousTelemetry = $env:PI_TELEMETRY
$PreviousPath = $env:PATH
$env:PI_CODING_AGENT_DIR = $PiCtfRoot
$env:PI_CACHE_RETENTION = "long"
$env:PI_SKIP_VERSION_CHECK = "1"
$env:PI_TELEMETRY = "0"
if (Test-Path -LiteralPath $HypaPath -PathType Leaf) {
    $env:PATH = "$(Split-Path -Parent $HypaPath);$env:PATH"
}

try {
    if ($Login) {
        Push-Location -LiteralPath $ResolvedWorkspace
        try {
            Write-Host "In Pi, run: /login openai-codex"
            & $Pi --no-extensions --no-skills --no-prompt-templates --no-context-files --no-themes --no-approve
            $ExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        exit $ExitCode
    }

    & $Pi auth check --provider $Provider --json --no-refresh *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Pi CTF profile is not authenticated for $Provider. Run scripts\start-pi-ctf.ps1 -Category $Category -Login"
    }

    Push-Location -LiteralPath $ResolvedWorkspace
    try {
        & $Pi @PiArguments
        $ExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    exit $ExitCode
}
finally {
    $env:PI_CODING_AGENT_DIR = $PreviousAgentDir
    $env:PI_CACHE_RETENTION = $PreviousCacheRetention
    $env:PI_SKIP_VERSION_CHECK = $PreviousSkipVersionCheck
    $env:PI_TELEMETRY = $PreviousTelemetry
    $env:PATH = $PreviousPath
}
