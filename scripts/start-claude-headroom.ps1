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

# A custom Anthropic base URL otherwise makes Claude load every MCP schema eagerly.
$env:ENABLE_TOOL_SEARCH = "1"
& $Headroom wrap claude --code-memory none --tool-search true -- @AgentArguments
if ($LASTEXITCODE -ne 0) {
    throw "Headroom-wrapped Claude Code exited with code $LASTEXITCODE."
}
