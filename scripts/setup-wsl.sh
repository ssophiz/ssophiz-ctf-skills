#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
mode="${1:-all}"

install_packages() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Package installation must run as root. Use setup-wsl.ps1 or: wsl -d Ubuntu -u root -- bash scripts/setup-wsl.sh packages" >&2
    exit 77
  fi
  apt-get update
  apt-get install -y --no-install-recommends \
    binutils build-essential ca-certificates clang cmake curl default-jre-headless file gdb gdbserver git \
    jq libcapstone-dev libffi-dev libssl-dev ltrace make netcat-openbsd ninja-build nmap nodejs npm \
    patchelf pkg-config python3 python3-dev python3-pip python3-venv qemu-user qemu-user-static \
    radare2 ruby-full socat sqlmap strace tshark unzip wget xxd zip
}

install_user_tools() {
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "User tool installation must run as the default WSL user, not root." >&2
    exit 78
  fi
  python3 -m venv "$HOME/.venvs/ssophiz-ctf"
  "$HOME/.venvs/ssophiz-ctf/bin/python" -m pip install --upgrade pip wheel
  "$HOME/.venvs/ssophiz-ctf/bin/python" -m pip install \
    angr capstone cryptography keystone-engine pwntools requests ropper unicorn volatility3 z3-solver

  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI is not visible in Ubuntu. Enable Docker Desktop > Settings > Resources > WSL Integration > Ubuntu."
  fi

  echo "WSL CTF user toolchain installed. Python environment: $HOME/.venvs/ssophiz-ctf"
}

case "$mode" in
  packages) install_packages ;;
  user) install_user_tools ;;
  all)
    install_packages
    install_user_tools
    ;;
  *)
    echo "Usage: $0 [packages|user|all]" >&2
    exit 64
    ;;
esac
