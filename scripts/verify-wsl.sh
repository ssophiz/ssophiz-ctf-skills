#!/usr/bin/env bash
set -euo pipefail

required=(bash file gdb python3 r2 readelf objdump patchelf strace ltrace nc socat jq)
missing=()
for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing+=("$command_name")
  fi
done

if ((${#missing[@]})); then
  printf 'Missing required commands: %s\n' "${missing[*]}" >&2
  exit 1
fi

"$HOME/.venvs/ssophiz-ctf/bin/python" -c 'import angr, pwn, ropper, z3; print("Python CTF packages: OK")'
uname -a
python3 --version
gdb --version | head -n 1
r2 -v | head -n 1
if command -v docker >/dev/null 2>&1; then
  docker version --format 'Docker client={{.Client.Version}} server={{.Server.Version}}' || true
fi
echo "WSL CTF verification: OK"
