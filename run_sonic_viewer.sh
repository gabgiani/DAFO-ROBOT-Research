#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h}"
SSH_KEY="${SONIC_SSH_KEY:-$HOME/.ssh/dafomes_lan}"
SSH_HOST="${SONIC_SSH_HOST:-nvidia@192.168.0.60}"
LOCAL_PORT="${SONIC_LOCAL_PORT:-5557}"
REMOTE_PORT="${SONIC_REMOTE_PORT:-5557}"
CONTROL_PORT="${SONIC_CONTROL_PORT:-5556}"
PHYSICAL_PORT="${SONIC_PHYSICAL_PORT:-5558}"
REMOTE_ROOT="${SONIC_REMOTE_ROOT:-/home/nvidia/GR00T-WholeBodyControl}"

cd "$ROOT"

scp -q -i "$SSH_KEY" -o BatchMode=yes sonic_physical_pose_relay.py \
  "$SSH_HOST:/tmp/sonic_physical_pose_relay.py"

ssh -i "$SSH_KEY" -o BatchMode=yes "$SSH_HOST" \
  "pkill -f '[s]onic_physical_pose_relay.py' 2>/dev/null || true"

ssh -i "$SSH_KEY" -o BatchMode=yes "$SSH_HOST" \
  "cd '$REMOTE_ROOT' && nohup .venv_sim/bin/python /tmp/sonic_physical_pose_relay.py \
  >/tmp/sonic_physical_pose_relay.log 2>&1 </dev/null &"

ssh -i "$SSH_KEY" -o BatchMode=yes -o ExitOnForwardFailure=yes -N \
  -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
  -L "${PHYSICAL_PORT}:127.0.0.1:${PHYSICAL_PORT}" \
  -R "${CONTROL_PORT}:127.0.0.1:${CONTROL_PORT}" "$SSH_HOST" &
TUNNEL_PID=$!
trap 'kill "$TUNNEL_PID" 2>/dev/null || true' EXIT INT TERM

.venv/bin/mjpython sonic_viewer.py \
  --url "tcp://127.0.0.1:${LOCAL_PORT}" \
  --physical-url "tcp://127.0.0.1:${PHYSICAL_PORT}"