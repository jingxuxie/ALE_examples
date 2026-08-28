#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${ALE_ASSETS:?Set ALE_ASSETS to the supplied assets directory}"
export TMPDIR="$HERE/tmp"
mkdir -p "$TMPDIR"
source "$ALE_ASSETS/workspace/env.sh"
export PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$TMPDIR/matplotlib"
python3 "$HERE/workspace/package_evidence.py"
python3 "$HERE/workspace/verify.py"
python3 "$HERE/workspace/report.py"
