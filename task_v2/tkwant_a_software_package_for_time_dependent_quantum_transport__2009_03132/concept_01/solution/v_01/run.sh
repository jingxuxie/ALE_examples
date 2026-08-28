#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/workspace"
exec bash run.sh "$@"
