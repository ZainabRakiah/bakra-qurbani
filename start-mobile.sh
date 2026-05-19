#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export BAKRA_HOST="${BAKRA_HOST:-0.0.0.0}"
export BAKRA_PORT="${BAKRA_PORT:-8000}"

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo "Bakra Bazaar mobile testing"
echo "Desktop URL: http://127.0.0.1:${BAKRA_PORT}"
if [[ -n "${LAN_IP}" ]]; then
  echo "Phone URL:   http://${LAN_IP}:${BAKRA_PORT}"
else
  echo "Phone URL:   http://<your-computer-ip>:${BAKRA_PORT}"
fi
echo
echo "Keep this terminal open while testing on Android."
echo "Make sure the phone and computer are on the same Wi-Fi."
echo

if lsof -ti :"${BAKRA_PORT}" >/dev/null 2>&1; then
  echo "Port ${BAKRA_PORT} is already in use — Bakra Bazaar may already be running."
  echo "Open http://127.0.0.1:${BAKRA_PORT} or stop the old server:"
  echo "  lsof -ti :${BAKRA_PORT} | xargs kill"
  exit 1
fi

python3 server.py
