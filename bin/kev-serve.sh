#!/usr/bin/env bash
# 启动 Kev 决策服务 决策服务(GPU 生命周期由 nvidia-run 托管)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEV_DIR="$ROOT/vendor/kev"
cd "$KEV_DIR"
# 4B bf16 权重 + CUDA graph 池超过 12GB 卡容量,默认关 graphs(~950ms/帧);要 0.8B 用 KEV_RUN=jaredpalmer/kev-0.8b
export KEV_CUDA_GRAPHS="${KEV_CUDA_GRAPHS:-0}"
exec nvidia-run -- .venv/bin/python -m kev.serve --run "${KEV_RUN:-$ROOT/artifacts/models/kev-4b}" --host 127.0.0.1 --port 8208
