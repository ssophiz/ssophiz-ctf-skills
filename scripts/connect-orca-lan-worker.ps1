[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^orca://pair\?")]
    [string]$PairingCode,

    [string]$Name = "cce-laptop-2",

    [string]$RemoteRepoPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

if (-not (Get-Command orca -ErrorAction SilentlyContinue)) {
    throw "Required command is missing: orca"
}

$existing = (& orca environment list --json | ConvertFrom-Json).result.environments |
    Where-Object { $_.name -eq $Name }
if ($existing) {
    throw "An Orca environment named '$Name' already exists. Remove it explicitly or choose another -Name."
}

Write-Host "Registering remote Orca worker environment '$Name'..."
& orca environment add --name $Name --pairing-code $PairingCode --json
if ($LASTEXITCODE -ne 0) {
    throw "Remote environment registration failed with exit code $LASTEXITCODE"
}

Write-Host "Checking the remote runtime..."
& orca status --environment $Name --json
if ($LASTEXITCODE -ne 0) {
    throw "The environment was saved, but the remote runtime health check failed."
}

if ($RemoteRepoPath) {
    Write-Host "Registering remote repository path '$RemoteRepoPath'..."
    & orca repo add --environment $Name --path $RemoteRepoPath --json
    if ($LASTEXITCODE -ne 0) {
        throw "Remote runtime connected, but repository registration failed. Verify -RemoteRepoPath on the worker PC."
    }
}

Write-Host "Remote worker '$Name' is ready."
Write-Host "Example: orca orchestration worker-start --task <task_id> --on $Name --worktree new-top-level --repo name:ssophiz-ctf-skills --agent codex --model gpt-5.6-sol --effort xhigh --name <worker-name> --json"
