#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ASSETS=${ALE_ASSETS:-$(cd "$HERE/../../participant/v_01" && pwd)}
source "$ASSETS/workspace/env.sh"
exec python3 "$ASSETS/workspace/legacy/run.py" "$@"
