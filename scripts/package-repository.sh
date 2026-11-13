#!/usr/bin/env bash
set -euo pipefail
helm_bin=${HELM:-helm}
mkdir -p helm-repository
"$helm_bin" package charts/vendored-litmus --destination helm-repository
args=()
if [[ -f helm-repository/index.yaml ]]; then
  args+=(--merge helm-repository/index.yaml)
fi
"$helm_bin" repo index helm-repository \
  "${args[@]}"
python3 scripts/check-package.py
