#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
.venv/bin/python teleop_unitree.py --host 127.0.0.1 --port 47001
