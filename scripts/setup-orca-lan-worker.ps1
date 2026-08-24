[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 6770,

    [string]$PairingAddress = "",

    [switch]$SkipPythonSetup,

    [switch]$Offline,

    [switch]$StrictDoctor,

    [switch]$PrepareOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command is missing: $Name"
    }
}

function Install-ProjectSkills {
    param([Parameter(Mandatory = $true)][string]$Root)

    $skillNames = @(
        "web", "pwn", "reverse", "crypto",
        "forensics", "malware", "misc", "orchestrator"
    )
    $targetRoots = @(
        (Join-Path $env:USERPROFILE ".agents\skills"),
        (Join-Path $env:USERPROFILE ".claude\skills"),
        (Join-Path $env:USERPROFILE ".codex\skills")
    )

    foreach ($targetRoot in $targetRoots) {
        New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
        foreach ($skillName in $skillNames) {
            $source = Join-Path $Root "skills\$skillName"
            if (-not (Test-Path -LiteralPath (Join-Path $source "SKILL.md"))) {
                throw "Project skill is incomplete: $source"
            }
            $destination = Join-Path $targetRoot "ssophiz-ctf-$skillName"
            New-Item -ItemType Directory -Force -Path $destination | Out-Null
            Copy-Item -LiteralPath (Join-Path $source "SKILL.md") -Destination $destination -Force

            foreach ($optionalDirectory in @("assets", "references", "scripts", "templates")) {
                $optionalSource = Join-Path $source $optionalDirectory
                if (Test-Path -LiteralPath $optionalSource) {
                    $optionalDestination = Join-Path $destination $optionalDirectory
                    New-Item -ItemType Directory -Force -Path $optionalDestination | Out-Null
                    Copy-Item -Path (Join-Path $optionalSource "*") -Destination $optionalDestination -Recurse -Force
                }
            }
        }
    }
}

function Install-BundledOrcaSkillsOffline {
    $targetRoots = @(
        (Join-Path $env:USERPROFILE ".agents\skills"),
        (Join-Path $env:USERPROFILE ".claude\skills"),
        (Join-Path $env:USERPROFILE ".codex\skills")
    )
    foreach ($skillName in @("orca-cli", "orchestration")) {
        $markdown = (& orca skills get $skillName --full | Out-String)
        if ($LASTEXITCODE -ne 0 -or -not $markdown.Trim()) {
            throw "Could not read bundled Orca skill: $skillName"
        }
        foreach ($targetRoot in $targetRoots) {
            $destination = Join-Path $targetRoot $skillName
            New-Item -ItemType Directory -Force -Path $destination | Out-Null
            Set-Content -LiteralPath (Join-Path $destination "SKILL.md") -Value $markdown -Encoding utf8
        }
    }
}

function Get-LanIPv4 {
    $candidate = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Where-Object { $_ -and $_ -notmatch "^(127\.|169\.254\.)" } |
        Select-Object -First 1
    if (-not $candidate) {
        throw "Could not determine a LAN IPv4 address. Pass -PairingAddress explicitly."
    }
    return $candidate
}

Require-Command "orca"
Require-Command "python"

Write-Host "[1/4] Installing Orca coordination skills for Claude Code and Codex..."
if (-not $Offline) {
    & orca skills install --skill orca-cli --skill orchestration --agent claude-code,codex
}
if ($Offline -or $LASTEXITCODE -ne 0) {
    Write-Warning "Online Orca skill installation is unavailable; using the guides bundled in the local Orca CLI."
    Install-BundledOrcaSkillsOffline
}

Write-Host "[2/4] Installing the repository CTF skills into agent discovery paths..."
Install-ProjectSkills -Root $RepoRoot

if (-not $SkipPythonSetup) {
    Write-Host "[3/4] Preparing the project virtual environment and running doctor..."
    if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Virtual environment creation failed with exit code $LASTEXITCODE"
        }
    }
    & ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Project installation failed with exit code $LASTEXITCODE"
    }
    & ".\scripts\ctf-harness.ps1" doctor
    if ($LASTEXITCODE -ne 0) {
        if ($StrictDoctor) {
            throw "Harness doctor failed with exit code $LASTEXITCODE"
        }
        Write-Warning "Harness doctor reported missing optional tooling. Orca pairing will continue; rerun doctor later to identify the unavailable checks."
    }
}
else {
    Write-Host "[3/4] Python setup skipped by request."
}

if (-not $PairingAddress) {
    $PairingAddress = Get-LanIPv4
}

Write-Host "[4/4] Worker prepared. LAN address: $PairingAddress, port: $Port"
if ($PrepareOnly) {
    Write-Host "Preparation-only mode complete."
    Write-Host "Start later with: orca serve --port $Port --pairing-address $PairingAddress"
    exit 0
}

Write-Host "Keep this terminal open and send the printed orca://pair?... code to the coordinator PC."
Write-Host "If Windows Firewall prompts, allow Orca on Private networks only."
& orca serve --port $Port --pairing-address $PairingAddress
