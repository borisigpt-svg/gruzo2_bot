#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-gruzo2_bot}"
WINDOW_MINUTES="${WINDOW_MINUTES:-10}"

echo "[healthcheck] service=${SERVICE_NAME} window=${WINDOW_MINUTES}m"

# 1) systemd active?
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[FAIL] systemd: $SERVICE_NAME is not active"
  systemctl status "$SERVICE_NAME" --no-pager || true
  exit 2
fi
echo "[OK] systemd active"

# 2) Recent logs sanity: look for polling start / activity keywords
since="${WINDOW_MINUTES} minutes ago"
logs="$(journalctl -u "$SERVICE_NAME" --since "$since" --no-pager 2>/dev/null || true)"

if [[ -z "${logs}" ]]; then
  echo "[WARN] no logs in window (${WINDOW_MINUTES}m). Not failing hard, but investigate."
  exit 0
fi

# Heuristics: accept either "Start polling" or any mention of "polling"
if echo "$logs" | grep -Eqi "Start polling|polling"; then
  echo "[OK] recent logs show polling activity"
  exit 0
fi

echo "[WARN] no polling keywords found in recent logs. This may still be OK depending on bot implementation."
echo "[INFO] last 40 lines:"
echo "$logs" | tail -n 40
exit 0
