[CmdletBinding()]
param(
    [string]$CertificatePath
)

$ErrorActionPreference = 'Stop'
$ExpectedSha256 = 'F0CD241634F90B44853096EAA6D064529C09ED0042AF6799BE8796DD5B252C35'
$ExpectedThumbprint = 'F7E8D8C50644A783F29607766F0A48A8D58497BF'

if ([string]::IsNullOrWhiteSpace($CertificatePath)) {
    $CertificatePath = Join-Path $PSScriptRoot '..\analysis\netshare-root.pem'
}

$resolvedPath = (Resolve-Path -LiteralPath $CertificatePath).Path
$pem = Get-Content -LiteralPath $resolvedPath -Raw
$base64 = ($pem -replace '-----BEGIN CERTIFICATE-----', '' -replace '-----END CERTIFICATE-----', '' -replace '\s', '')
$raw = [Convert]::FromBase64String($base64)

$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    $actualSha256 = ([BitConverter]::ToString($sha256.ComputeHash($raw))).Replace('-', '')
}
finally {
    $sha256.Dispose()
}

if ($actualSha256 -ne $ExpectedSha256) {
    throw "Refusing to install: certificate SHA-256 mismatch. Expected $ExpectedSha256, got $actualSha256"
}

$certificate = New-Object Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList (, $raw)
if ($certificate.Thumbprint -ne $ExpectedThumbprint) {
    throw "Refusing to install: certificate thumbprint mismatch. Expected $ExpectedThumbprint, got $($certificate.Thumbprint)"
}

$existing = Get-ChildItem -Path "Cert:\CurrentUser\Root\$ExpectedThumbprint" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "NetShare root is already installed for the current user: $ExpectedThumbprint"
    exit 0
}

$store = New-Object Security.Cryptography.X509Certificates.X509Store('Root', 'CurrentUser')
try {
    $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $store.Add($certificate)
}
finally {
    $store.Close()
    $certificate.Dispose()
}

Write-Host "Installed NetShare root in CurrentUser Root: $ExpectedThumbprint"
Write-Warning 'This certificate permits NetShare to intercept HTTPS for this Windows user. Remove it after the CTF with scripts\remove_netshare_root.ps1.'
