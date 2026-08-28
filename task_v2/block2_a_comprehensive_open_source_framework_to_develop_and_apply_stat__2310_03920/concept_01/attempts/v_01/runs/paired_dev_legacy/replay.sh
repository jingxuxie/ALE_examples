#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${ALE_ASSETS:?}/workspace/env.sh"
export PYTHONDONTWRITEBYTECODE=1
unset LEGACY_REPAIR_CLOCK LEGACY_REPAIR_U
python3 "$HERE/../../workspace/legacy/run.py" "$HERE/case.json" "${1:?Provide an empty replay directory}" production
