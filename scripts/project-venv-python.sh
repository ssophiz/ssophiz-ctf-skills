#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
project_python="$repo_root/.venv/bin/python"
if [[ ! -x "$project_python" ]]; then
  printf 'Project virtual environment not found: %s\n' "$project_python" >&2
  exit 2
fi
cd -- "$repo_root"
exec "$project_python" "$@"
