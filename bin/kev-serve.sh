#!/usr/bin/env bash
# 启动 Kev 决策服务 决策服务(GPU 生命周期由 nvidia-run 托管)
set -euo pipefail
KEV_DIR="$(cd "$(dirname "$0")/../vendor/kev" && pwd)"
cd "$KEV_DIR"
exec nvidia-run -- .venv/bin/python -m kev.serve --run "${KEV_RUN:-jaredpalmer/kev-0.8b}" --host 127.0.0.1 --port 8208
