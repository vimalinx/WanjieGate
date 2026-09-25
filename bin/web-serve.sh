#!/usr/bin/env bash
# 静态页面服务 (manifest + 前端,决策调用直连 kev :8008)
set -euo pipefail
cd "$(dirname "$0")/../static"
exec python3 -m http.server 5173 --bind 127.0.0.1
