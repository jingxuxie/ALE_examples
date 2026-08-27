#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
cd "$ROOT"
mkdir -p logs diagnostics validation
bash "$HERE/python.sh" "$HERE/validate.py" validation/tests.json > logs/tests.log 2>&1
bash "$HERE/python.sh" "$HERE/run_public.py" > logs/public_final.log 2>&1
bash "$HERE/python.sh" "$HERE/experiments.py" > logs/experiments.log 2>&1
bash "$HERE/python.sh" "$HERE/diagnose.py" input/cases/driven_static.json diagnostics/driven_static_mc.json --batches 16 --batch-size 512 --seed 4217 > logs/diagnostic_static.log 2>&1
bash "$HERE/python.sh" "$HERE/diagnose.py" input/cases/memory_ou.json diagnostics/memory_ou_mc.json --batches 16 --batch-size 256 --max-step 0.01 --seed 4217 > logs/diagnostic_ou.log 2>&1
bash "$HERE/python.sh" "$HERE/diagnose.py" input/cases/switching_echo.json diagnostics/switching_coarse_mc.json --batches 16 --batch-size 512 --max-step 0.02 --seed 4217 > logs/diagnostic_switch_coarse.log 2>&1
bash "$HERE/python.sh" "$HERE/diagnose.py" input/cases/switching_echo.json diagnostics/switching_fine_mc.json --batches 16 --batch-size 512 --max-step 0.005 --seed 4217 > logs/diagnostic_switch_fine.log 2>&1
bash "$HERE/python.sh" "$HERE/build_evidence.py"
bash "$HERE/python.sh" "$HERE/verify_deliverables.py"
