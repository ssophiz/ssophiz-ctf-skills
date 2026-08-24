[CmdletBinding()]
param(
    [string]$ProxyUrl = $env:CCE_PROXY_URL,
    [string]$PonytailRef = "2ed6c52c9d7e5e56942508591085fd45dea277d3",
    [string]$GraphifyVersion = "0.9.48",
    [switch]$SkipProjectGraphify
)

$ErrorActionPreference = "Stop"
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

$Codex = (Get-Command codex -ErrorAction Stop).Source
$Node = Get-Command node -ErrorAction SilentlyContinue
if (-not $Node) {
    Write-Warning "Node.js is not on PATH. Ponytail installs, but its lifecycle hooks remain inactive until Node.js is available."
}

Write-Host "[1/4] Installing Ponytail for Codex..."
$Marketplaces = (& $Codex plugin marketplace list | Out-String)
if ($Marketplaces -notmatch '(?m)^ponytail\s') {
    Invoke-Checked $Codex plugin marketplace add DietrichGebert/ponytail --ref $PonytailRef --json
}
$Plugins = (& $Codex plugin list | Out-String)
if ($Plugins -notmatch 'ponytail@ponytail\s+installed, enabled') {
    Invoke-Checked $Codex plugin add ponytail@ponytail --json
}

Write-Host "[2/4] Ensuring uv is available..."
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvCommand) {
    $UvCandidate = Get-ChildItem -Path (Join-Path $env:APPDATA 'Python\Python*\Scripts\uv.exe') -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $UvCandidate) {
        $Py = Get-Command py -ErrorAction SilentlyContinue
        if (-not $Py) {
            throw "Python launcher 'py' is required to bootstrap uv."
        }
        Invoke-Checked $Py.Source -3 -m pip install --user uv
        $UvCandidate = Get-ChildItem -Path (Join-Path $env:APPDATA 'Python\Python*\Scripts\uv.exe') -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
    }
    if (-not $UvCandidate) {
        throw "uv installed, but uv.exe was not found under the user Python Scripts directory."
    }
    $UvPath = $UvCandidate.FullName
} else {
    $UvPath = $UvCommand.Source
}

Write-Host "[3/4] Installing Graphify $GraphifyVersion..."
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

$FeatureState = (& $Codex features list | Select-String -Pattern '^multi_agent\s').Line
if ($FeatureState -notmatch 'true\s*$') {
    Invoke-Checked $Codex features enable multi_agent
}

Write-Host "[4/4] Verifying installations..."
Invoke-Checked $GraphifyPath --version
$PluginState = (& $Codex plugin list | Out-String)
if ($PluginState -notmatch 'ponytail@ponytail\s+installed, enabled') {
    throw "Ponytail is not enabled after installation."
}

Write-Host "Ponytail and Graphify are ready. Restart Codex, review Ponytail in /hooks, then start a new thread."
