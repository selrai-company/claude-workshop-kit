#!/usr/bin/env bash
# Offline: runs the server's built-in selftest (no network, no credentials).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/saasu_mcp.py selftest
