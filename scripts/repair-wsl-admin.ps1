# Run from an elevated PowerShell. This script never unregisters or deletes a distribution.
$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator PowerShell is required. No changes were made."
}

Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
wsl --update
wsl --set-default-version 2

$ubuntuEntry = Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' -ErrorAction SilentlyContinue |
    ForEach-Object { Get-ItemProperty $_.PSPath } |
    Where-Object DistributionName -eq 'Ubuntu'

if (-not $ubuntuEntry) {
    wsl --install -d Ubuntu --no-launch
}

Write-Output "WSL features are enabled. Reboot Windows, then run scripts/setup-wsl.ps1 in a normal PowerShell."
