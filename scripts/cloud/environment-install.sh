#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
git submodule update --init --recursive
python3 - <<'PY'
import json,subprocess
for m in json.load(open('scripts/cloud/checkpoint.json'))['submodules']:
    assert subprocess.check_output(['git','-C',m['path'],'rev-parse','HEAD'],text=True).strip()==m['commit'],m['path']
PY
bash scripts/cloud/install-agent.sh
