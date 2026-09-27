#!/usr/bin/env python3
"""Offline regression suite. Live browser/provider checks are recorded separately."""
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for command in ([sys.executable,'-m','unittest','tools.test_workbench','tools.test_api','tools.test_live_runtime','-v'],['node','tools/test_composition.mjs'],['node','tools/test_live.mjs']):
    result=subprocess.run(command,cwd=root)
    if result.returncode: raise SystemExit(result.returncode)
