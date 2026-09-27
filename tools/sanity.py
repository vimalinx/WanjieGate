#!/usr/bin/env python3
"""Compatibility entry for the current KEV probe."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('probe4b.py')),run_name='__main__')
