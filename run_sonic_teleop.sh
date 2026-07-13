#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h}"
cd "$ROOT"
exec .venv/bin/python sonic_teleop.py "$@"