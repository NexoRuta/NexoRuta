#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Installation never selects a historical checkpoint or rewrites a submodule.
python3 scripts/cloud/verify-gitlinks.py
bash scripts/cloud/install-agent.sh
