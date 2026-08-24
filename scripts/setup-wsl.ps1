$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

$drive = ([IO.Path]::GetPathRoot($RepoRoot)).TrimEnd('\').TrimEnd(':').ToLowerInvariant()
$relative = $RepoRoot.Substring(3).Replace('\', '/')
$wslRepo = "/mnt/$drive/$relative"

$probe = Start-Process -FilePath wsl.exe -ArgumentList @('-d', 'Ubuntu', '--', '/bin/true') -WindowStyle Hidden -PassThru
try {
    Wait-Process -Id $probe.Id -Timeout 20 -ErrorAction Stop
} catch {
    Stop-Process -Id $probe.Id -Force -ErrorAction SilentlyContinue
    throw "Ubuntu WSL did not start within 20 seconds. Run scripts/repair-wsl-admin.ps1 as Administrator and reboot first."
}
if ($probe.ExitCode -ne 0) {
    throw "Ubuntu WSL probe failed with exit code $($probe.ExitCode)."
}

wsl -d Ubuntu -u root -- bash "$wslRepo/scripts/setup-wsl.sh" packages
wsl -d Ubuntu -- bash "$wslRepo/scripts/setup-wsl.sh" user
wsl -d Ubuntu -- bash "$wslRepo/scripts/verify-wsl.sh"

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker info *> $null
$dockerReady = $LASTEXITCODE -eq 0
$ErrorActionPreference = $previousPreference

if ($dockerReady) {
    docker build -t ssophiz-ctf-worker:latest (Join-Path $RepoRoot 'docker\worker')
} else {
    Write-Warning "Docker Desktop is not responding. Start Docker Desktop, enable Ubuntu WSL integration, then build docker/worker."
}
