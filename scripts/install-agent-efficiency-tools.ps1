[CmdletBinding()]
param(
    [string]$ProxyUrl = $env:CCE_PROXY_URL,
    [string]$PonytailRef = "2ed6c52c9d7e5e56942508591085fd45dea277d3",
    [string]$GraphifyVersion = "0.9.48",
    [string]$HeadroomVersion = "0.36.5",
    [string]$CodeBurnVersion = "0.9.20",
    [string]$CavemanRef = "7bb71309e8749a4f112aacd3a54b3941d8689905",
    [string]$ImpeccableRef = "c3a30086bc395ea2197fbe287dc59c18969aaeb6",
    [switch]$SkipProjectGraphify
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:\PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

if ($ProxyUrl) {
    $env:HTTP_PROXY = $ProxyUrl
    $env:HTTPS_PROXY = $ProxyUrl
    $env:ALL_PROXY = $ProxyUrl
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Install-PinnedSkills {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$Ref,
        [Parameter(Mandatory = $true)][hashtable]$SkillPaths
    )

    $TempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $TempRoot = Join-Path $TempBase ("ssophiz-agent-skill-" + [Guid]::NewGuid().ToString("N"))
    $CloneRoot = Join-Path $TempRoot "repo"
    New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

    try {
        Invoke-Checked git clone --filter=blob:none --no-checkout "https://github.com/$Repository.git" $CloneRoot
        Invoke-Checked git -C $CloneRoot fetch --depth 1 origin $Ref
        Invoke-Checked git -C $CloneRoot checkout --detach $Ref

        $TargetRoots = @(
            (Join-Path $env:USERPROFILE ".agents\skills"),
            (Join-Path $env:USERPROFILE ".claude\skills")
        )
        foreach ($TargetRoot in $TargetRoots) {
            New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null
            foreach ($Entry in $SkillPaths.GetEnumerator()) {
                $Source = Join-Path $CloneRoot $Entry.Key
                if (-not (Test-Path -LiteralPath (Join-Path $Source "SKILL.md"))) {
                    throw "Pinned skill is incomplete: $Repository/$($Entry.Key)@$Ref"
                }
                $Destination = Join-Path $TargetRoot $Entry.Value
                New-Item -ItemType Directory -Force -Path $Destination | Out-Null
                Copy-Item -Path (Join-Path $Source "*") -Destination $Destination -Recurse -Force
            }
        }
    }
    finally {
        $ResolvedTemp = [System.IO.Path]::GetFullPath($TempRoot)
        if ($ResolvedTemp.StartsWith($TempBase, [System.StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $ResolvedTemp) -like "ssophiz-agent-skill-*") {
            Remove-Item -LiteralPath $ResolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

$Codex = (Get-Command codex -ErrorAction Stop).Source
$Node = Get-Command node -ErrorAction Stop
$Npm = (Get-Command npm -ErrorAction Stop).Source
$Python = (Get-Command python -ErrorAction Stop).Source

Write-Host "[1/8] Installing Ponytail as an on-demand skill..."
Install-PinnedSkills -Repository "DietrichGebert/ponytail" -Ref $PonytailRef -SkillPaths @{
    "skills/ponytail" = "ponytail"
}

Write-Host "[2/8] Ensuring uv is available..."
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvCommand) {
    $UvCandidate = Get-ChildItem -Path (Join-Path $env:APPDATA 'Python\Python*\Scripts\uv.exe') -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $UvCandidate) {
        Invoke-Checked $Python -m pip install --user uv
        $UvCandidate = Get-ChildItem -Path (Join-Path $env:APPDATA 'Python\Python*\Scripts\uv.exe') -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
    }
    if (-not $UvCandidate) {
        throw "uv installed, but uv.exe was not found under the user Python Scripts directory."
    }
    $UvPath = $UvCandidate.FullName
}
else {
    $UvPath = $UvCommand.Source
}

Write-Host "[3/8] Installing Graphify $GraphifyVersion..."
Invoke-Checked $UvPath tool install --upgrade "graphifyy==$GraphifyVersion"
Invoke-Checked $UvPath tool update-shell
$GraphifyPath = Join-Path $env:USERPROFILE '.local\bin\graphify.exe'
if (-not (Test-Path -LiteralPath $GraphifyPath)) {
    $GraphifyCommand = Get-Command graphify -ErrorAction SilentlyContinue
    if (-not $GraphifyCommand) {
        throw "Graphify installed, but graphify.exe was not found. Restart the shell and run this script again."
    }
    $GraphifyPath = $GraphifyCommand.Source
}
if (-not $SkipProjectGraphify) {
    Invoke-Checked $GraphifyPath install --project --platform codex
}

Write-Host "[4/8] Installing Headroom $HeadroomVersion in an isolated environment..."
$HeadroomEnv = Join-Path $env:USERPROFILE '.local\share\headroom-venv'
$HeadroomPython = Join-Path $HeadroomEnv 'Scripts\python.exe'
$HeadroomPath = Join-Path $HeadroomEnv 'Scripts\headroom.exe'
if (-not (Test-Path -LiteralPath $HeadroomPython)) {
    Invoke-Checked $Python -m venv $HeadroomEnv
}
Invoke-Checked $HeadroomPython -m pip install --upgrade "headroom-ai[proxy,mcp]==$HeadroomVersion"

Write-Host "[5/8] Installing CodeBurn $CodeBurnVersion..."
Invoke-Checked $Npm install -g "codeburn@$CodeBurnVersion"

Write-Host "[6/8] Installing Caveman skills without proxy hooks..."
Install-PinnedSkills -Repository "JuliusBrussee/caveman" -Ref $CavemanRef -SkillPaths @{
    "skills/caveman" = "caveman"
    "skills/caveman-compress" = "caveman-compress"
}

Write-Host "[7/8] Installing Impeccable as an on-demand UI skill..."
Install-PinnedSkills -Repository "pbakaus/impeccable" -Ref $ImpeccableRef -SkillPaths @{
    "plugin/skills/impeccable" = "impeccable"
}

Write-Host "[8/8] Verifying installations..."
Invoke-Checked $GraphifyPath --version
Invoke-Checked $HeadroomPath --version
$CodeBurn = (Get-Command codeburn -ErrorAction Stop).Source
Invoke-Checked $CodeBurn --version
foreach ($Root in @('.agents\skills', '.claude\skills')) {
    foreach ($Skill in @('ponytail', 'caveman', 'caveman-compress', 'impeccable')) {
        $SkillFile = Join-Path (Join-Path $env:USERPROFILE $Root) "$Skill\SKILL.md"
        if (-not (Test-Path -LiteralPath $SkillFile)) {
            throw "Skill installation verification failed: $SkillFile"
        }
    }
}

$FeatureState = (& $Codex features list | Select-String -Pattern '^multi_agent\s').Line
if ($FeatureState -notmatch 'true\s*$') {
    Invoke-Checked $Codex features enable multi_agent
}

Write-Host "Agent-efficiency tools are ready. Restart agent sessions before using newly installed skills."
Write-Host "Headroom remains opt-in; use scripts\start-codex-headroom.ps1 or scripts\start-claude-headroom.ps1."
