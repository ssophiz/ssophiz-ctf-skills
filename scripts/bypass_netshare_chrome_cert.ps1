[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$windowResult = orca computer list-windows --app chrome --json | ConvertFrom-Json
if (-not $windowResult.ok) {
    throw 'Could not query Chrome windows through Orca computer control.'
}

$target = $windowResult.result.windows |
    Where-Object { $_.title -match '개인 정보 보호 오류|Privacy error|Your connection is not private' } |
    Select-Object -First 1

if (-not $target) {
    throw 'No Chrome certificate-warning window was found. Open the HTTPS site in Chrome first.'
}

$windowId = [long]$target.id
$clickX = [int]($target.width / 2)
$clickY = [int]($target.height / 2)

# Chromium recognizes this hidden phrase only while its certificate interstitial
# has page focus. The exception is scoped to the current browser session.
orca computer click --app chrome --window-id $windowId --x $clickX --y $clickY --restore-window --no-screenshot --json | Out-Null
orca computer type-text --app chrome --window-id $windowId --text thisisunsafe --restore-window --no-screenshot --json | Out-Null
Start-Sleep -Seconds 3

$state = orca computer get-app-state --app chrome --window-id $windowId --no-screenshot --json | ConvertFrom-Json
$treeText = $state.result.snapshot.treeText
if ($treeText -match 'ERR_CERT_INVALID|연결이 비공개로 설정되어 있지 않습니다|Your connection is not private') {
    throw 'Chrome stayed on the certificate warning page; click the page once and rerun this script.'
}

$currentTitle = $state.result.snapshot.window.title
Write-Host "Certificate interstitial bypassed for this Chrome session. Current page: $currentTitle"
