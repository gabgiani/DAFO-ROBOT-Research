#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# Mata cualquier visor anterior (heuristico o RL) antes de lanzar uno nuevo.
pkill -f "simulate_unitree.py" 2>/dev/null || true
pkill -f "simulate_g1_rl.py" 2>/dev/null || true
sleep 0.5

.venv/bin/mjpython simulate_g1_rl.py
