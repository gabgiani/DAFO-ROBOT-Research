#!/bin/zsh
set -euo pipefail

SSH_KEY="${SONIC_SSH_KEY:-$HOME/.ssh/dafomes_lan}"
SSH_HOST="${SONIC_SSH_HOST:-nvidia@192.168.0.60}"
REMOTE_ROOT="${SONIC_REMOTE_ROOT:-/home/nvidia/GR00T-WholeBodyControl/gear_sonic_deploy}"

ssh -tt -i "$SSH_KEY" -o BatchMode=yes "$SSH_HOST" \
  "cd '$REMOTE_ROOT' && ./target/release/g1_deploy_onnx_ref lo \
policy/low_latency/model_decoder.onnx /tmp/sonic_smoke_motion \
--planner-file planner/target_vel/V2/planner_sonic.onnx \
--planner-precision 16 \
--obs-config policy/low_latency/observation_config.yaml \
--encoder-file policy/low_latency/model_encoder.onnx \
--input-type zmq_manager \
--zmq-host 127.0.0.1 \
--zmq-port 5556 \
--output-type all \
--disable-crc-check"