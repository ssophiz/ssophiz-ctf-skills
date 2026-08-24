[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AgentArguments
)

$ErrorActionPreference = "Stop"
$Headroom = Join-Path $env:USERPROFILE '.local\share\headroom-venv\Scripts\headroom.exe'
if (-not (Test-Path -LiteralPath $Headroom)) {
    throw "Headroom is not installed. Run scripts\install-agent-efficiency-tools.ps1 first."
}

# Keep raw task artifacts on disk. This wrapper only optimizes traffic entering the model.
& $Headroom wrap codex --code-memory none -- @AgentArguments
if ($LASTEXITCODE -ne 0) {
    throw "Headroom-wrapped Codex exited with code $LASTEXITCODE."
}
