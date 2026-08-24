$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
& ".\.venv\Scripts\ctf-harness.exe" init
docker build -t ssophiz-ctf-worker:latest docker/worker
& ".\.venv\Scripts\ctf-harness.exe" doctor
