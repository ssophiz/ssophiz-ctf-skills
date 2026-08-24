$ErrorActionPreference = 'Continue'
$proxyUrl = if ($env:CCE_PROXY_URL) { $env:CCE_PROXY_URL } else { 'http://192.168.49.1:8282' }
$proxyUri = [Uri]$proxyUrl

$proxyTest = Test-NetConnection $proxyUri.Host -Port $proxyUri.Port -InformationLevel Quiet
Write-Output "NETSHARE_PROXY=$proxyTest ($proxyUrl)"

$targets = @('https://api.anthropic.com/', 'https://challenge.cce.kr/')
foreach ($target in $targets) {
    $status = & wsl.exe -d Ubuntu -- env `
        "HTTP_PROXY=$proxyUrl" "HTTPS_PROXY=$proxyUrl" `
        curl -k -sS -o /dev/null -w '%{http_code}' `
        --connect-timeout 8 --max-time 15 $target
    Write-Output "$target=$status"
}

$workerImage = docker image inspect ssophiz-ctf-worker:latest --format '{{.Id}}' 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Output "CTF_WORKER_IMAGE=$workerImage"
} else {
    Write-Output 'CTF_WORKER_IMAGE=MISSING'
}
