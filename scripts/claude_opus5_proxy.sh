#!/usr/bin/env bash
set -euo pipefail

export CCE_PROXY_URL="${CCE_PROXY_URL:-http://192.168.49.1:8282}"
export HTTP_PROXY="$CCE_PROXY_URL"
export HTTPS_PROXY="$CCE_PROXY_URL"
export http_proxy="$CCE_PROXY_URL"
export https_proxy="$CCE_PROXY_URL"

exec claude --model opus --effort max "$@"
