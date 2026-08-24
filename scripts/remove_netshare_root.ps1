$ErrorActionPreference = 'Stop'
$thumbprint = 'F7E8D8C50644A783F29607766F0A48A8D58497BF'
$certificatePath = "Cert:\CurrentUser\Root\$thumbprint"

if (Test-Path $certificatePath) {
    Remove-Item -LiteralPath $certificatePath -Force
    Write-Output "REMOVED_NETSHARE_ROOT=$thumbprint"
} else {
    Write-Output "NETSHARE_ROOT_NOT_FOUND=$thumbprint"
}
