#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper for the Python build pipeline.
python3 /opt/blackfong/installer/scripts/build.py "$@"
