#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
source "$ROOT/workspace/environment.sh"
exec python -m qualification.cli "$@"
