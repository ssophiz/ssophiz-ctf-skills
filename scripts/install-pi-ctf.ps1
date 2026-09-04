[CmdletBinding()]
param(
    [string]$PiVersion = "0.84.4",
    [string]$HypaVersion = "v0.1.14",
    [string]$HypaWinX64Sha256 = "8fc1e9a478619157c896fd9419244ee7d875b73cbc9150d2f4c724b7ce62ba41",
    [string]$HypaWinArm64Sha256 = "cee0b55e44928777574356d0ee0804b8fc71fe55ed1aa7b18c0fc2f36b29fb56",
    [string]$ProxyUrl = $env:CCE_PROXY_URL
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:\PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if ($ProxyUrl) {
    $env:HTTP_PROXY = $ProxyUrl
    $env:HTTPS_PROXY = $ProxyUrl
    $env:ALL_PROXY = $ProxyUrl
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

$Npm = (Get-Command npm -ErrorAction Stop).Source
Write-Host "[1/4] Installing Pi $PiVersion with lifecycle scripts disabled..."
Invoke-Checked $Npm install -g --ignore-scripts "@earendil-works/pi-coding-agent@$PiVersion"

Write-Host "[2/4] Installing checksum-pinned Hypa $HypaVersion..."
$Architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
switch ($Architecture) {
    "X64" {
        $AssetName = "hypa-win-x64.zip"
        $ExpectedHash = $HypaWinX64Sha256
    }
    "Arm64" {
        $AssetName = "hypa-win-arm64.zip"
        $ExpectedHash = $HypaWinArm64Sha256
    }
    default { throw "Unsupported Windows architecture for Hypa: $Architecture" }
}

$TempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$TempRoot = Join-Path $TempBase ("ssophiz-hypa-" + [Guid]::NewGuid().ToString("N"))
$Archive = Join-Path $TempRoot $AssetName
$Extracted = Join-Path $TempRoot "expanded"
$InstallRoot = Join-Path $env:USERPROFILE ".local\bin"
$HypaTarget = Join-Path $InstallRoot "hypa.exe"

New-Item -ItemType Directory -Force -Path $TempRoot, $Extracted, $InstallRoot | Out-Null
try {
    $VersionPath = $HypaVersion.TrimStart("v")
    $Uri = "https://github.com/Hypabolic/Hypa/releases/download/v$VersionPath/$AssetName"
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Archive
    $ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedHash.ToLowerInvariant()) {
        throw "Hypa archive checksum mismatch: expected $ExpectedHash, got $ActualHash"
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted -Force
    $HypaSource = Get-ChildItem -LiteralPath $Extracted -Filter "hypa.exe" -File -Recurse | Select-Object -First 1
    if (-not $HypaSource) {
        throw "The verified Hypa archive did not contain hypa.exe"
    }
    Copy-Item -LiteralPath $HypaSource.FullName -Destination $HypaTarget -Force
}
finally {
    $ResolvedTemp = [System.IO.Path]::GetFullPath($TempRoot)
    if ($ResolvedTemp.StartsWith($TempBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $ResolvedTemp) -like "ssophiz-hypa-*") {
        Remove-Item -LiteralPath $ResolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "[3/4] Writing an isolated low-context Pi CTF profile..."
$PiCtfRoot = Join-Path $env:USERPROFILE ".pi\ctf-agent"
New-Item -ItemType Directory -Force -Path $PiCtfRoot | Out-Null
$Settings = @'
{
  "defaultProvider": "openai-codex",
  "defaultThinkingLevel": "medium",
  "quietStartup": true,
  "showCacheMissNotices": true,
  "defaultProjectTrust": "never",
  "enableInstallTelemetry": false,
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  },
  "retry": {
    "enabled": true,
    "maxRetries": 1,
    "baseDelayMs": 1000,
    "provider": {
      "maxRetries": 0,
      "maxRetryDelayMs": 10000
    }
  },
  "defaultTools": ["read", "powershell", "edit", "write"],
  "enableSkillCommands": false,
  "packages": [],
  "extensions": [],
  "skills": [],
  "prompts": [],
  "themes": []
}
'@
# Avoid global packages and skills. The launcher supplies exactly one CTF skill.
[System.IO.File]::WriteAllText((Join-Path $PiCtfRoot "settings.json"), $Settings, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[4/4] Verifying the isolated lane..."
$Pi = (Get-Command pi -ErrorAction Stop).Source
Invoke-Checked $Pi --version
Invoke-Checked $HypaTarget --version
Invoke-Checked $HypaTarget doctor

Write-Host "Pi CTF lane ready: $PiCtfRoot"
Write-Host "Authentication is intentionally not copied. Run scripts\start-pi-ctf.ps1 -Login once."
