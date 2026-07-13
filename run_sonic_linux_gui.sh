#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/home/nvidia/GR00T-WholeBodyControl}"
VIEWER_ROOT="${SONIC_VIEWER_ROOT:-$SONIC_ROOT/dafo-human-sonic}"
DISPLAY="${DISPLAY:-:0}"
XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
MODEL="${SONIC_MODEL:-$VIEWER_ROOT/model/g1_29dof_with_hand_rev_1_0.xml}"

export DISPLAY XAUTHORITY

cd "$VIEWER_ROOT"
exec "$SONIC_ROOT/.venv_sim/bin/python" sonic_viewer.py \
  --url tcp://127.0.0.1:5557 \
  --physical-url tcp://127.0.0.1:5558 \
  --model "$MODEL"