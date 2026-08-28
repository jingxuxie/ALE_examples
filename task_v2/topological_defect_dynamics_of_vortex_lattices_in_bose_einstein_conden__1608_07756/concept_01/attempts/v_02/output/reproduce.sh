#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
cd "$root"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python workspace/test_calibration.py > experiments/repaired_tests.txt 2>&1
python workspace/test_validation.py > experiments/validation.txt 2>&1
python workspace/make_transfer.py experiments/transfer_input
python experiments/baseline/workspace/test_calibration.py > experiments/baseline/tests.txt 2>&1 || true
python experiments/baseline/workspace/cli.py inputs/calibration.json experiments/baseline/calibration > experiments/baseline/run.log 2>&1
python experiments/baseline/workspace/diagnose.py inputs/calibration.json experiments/baseline/calibration > experiments/baseline/diagnosis.jsonl
for variant in primary ablation refinement coarse; do
    case "$variant" in
        primary) configuration=config.json ;;
        ablation) configuration=ablation_config.json ;;
        refinement) configuration=refinement_config.json ;;
        coarse) configuration=experiments/coarse_config.json ;;
    esac
    bash run.sh "$root/inputs/campaign.json" "experiments/$variant" "$configuration" > "experiments/$variant.log" 2>&1
    if [ "$variant" != ablation ]; then
        bash run.sh "$root/inputs/calibration.json" "experiments/calibration_$variant" "$configuration" > "experiments/calibration_$variant.log" 2>&1
        bash run.sh "$root/experiments/transfer_input/manifest.json" "experiments/transfer_$variant" "$configuration" > "experiments/transfer_$variant.log" 2>&1
    fi
done
bash run.sh "$root/experiments/ultrafine_input/manifest.json" experiments/ultrafine experiments/ultrafine_config.json > experiments/ultrafine.log 2>&1
python workspace/independent_check.py > experiments/independent.log 2>&1
bash run.sh "$root/experiments/smoke_input/manifest.json" 'experiments/smoke result' > experiments/smoke.log 2>&1
python workspace/audit.py experiments/smoke_input/manifest.json 'experiments/smoke result' 'experiments/smoke result/audit.csv' >> experiments/smoke.log 2>&1
python workspace/analyze.py > experiments/analysis.log 2>&1
python workspace/plot_results.py > experiments/plot.log 2>&1
python workspace/write_report.py
python workspace/verify_handoff.py
