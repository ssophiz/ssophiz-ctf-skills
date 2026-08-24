$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$ProjectPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $ProjectPython -PathType Leaf)) {
    throw "Project virtual environment not found: $ProjectPython"
}
Push-Location -LiteralPath $RepoRoot
try {
    & $ProjectPython -m ssophiz_ctf @args
    $HarnessExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $HarnessExitCode
