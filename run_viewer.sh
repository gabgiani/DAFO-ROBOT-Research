#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# Mata cualquier visor anterior de este mismo repo antes de lanzar uno nuevo.
pkill -f "simulate_unitree.py" 2>/dev/null || true
sleep 0.5

.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer
