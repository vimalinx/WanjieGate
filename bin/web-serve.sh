#!/usr/bin/env bash
# 同源工作台 API + 静态页面，数据保存在本项目 .data/
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m backend.server "$@"
