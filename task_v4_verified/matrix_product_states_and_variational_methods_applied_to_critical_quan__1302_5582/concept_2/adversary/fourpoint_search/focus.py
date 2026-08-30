import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json

import numpy as np

from fourpoint import ExactTargets, TensorContractions, cauchy_determinant, check_fourpoint, high_precision_target, trusted_physics, write_json

AUTHORIZED_TENSOR = ROOT.parents[1] / "attempts" / "v_3" / "state.npz"


def main():
    quartets = [(0, left, left + gap, left + gap + right)
                for left, gap, right in itertools.product((16, 32, 64, 96), (32, 64, 96, 128), (16, 32, 64, 96))
                if left + gap + right <= 256]
    specification = {"status": "private proposal only; not a frozen or edited task target",
                     "definition": "left,right in {16,32,64,96}; gap in {32,64,96,128}; span<=256",
                     "quartets": quartets, "raw_relative_tolerance": 0.025,
                     "composite_covariance_relative_tolerance": 0.1,
                     "covariance_target_floor": 1e-6,
                     "retain_existing_v2_requirements": True}
    write_json(ROOT / "proposed_quartets.json", specification)
    checked = check_fourpoint(AUTHORIZED_TENSOR, quartets)
    write_json(ROOT / "focused_checker_score.json", checked)
    ranked = sorted(checked["records"], key=lambda record: record["covariance_relative_error"], reverse=True)
    anchors = [[0, 16, 112, 128], [0, 96, 224, 256], [0, 48, 80, 128],
               [0, 96, 160, 256], [0, 192, 320, 512], [0, 192, 448, 512], [0, 384, 512, 1024]]
    tensor = trusted_physics.load_tensor(AUTHORIZED_TENSOR)
    original = TensorContractions(tensor)
    original.prepare(1024)
    targets = ExactTargets(1024)
    generator = np.random.default_rng(8702)
    half = tensor.shape[1] // 2
    gauge = np.zeros((2 * half, 2 * half), dtype=np.complex128)
    for sector in range(2):
        random = generator.normal(size=(half, half)) + 1j * generator.normal(size=(half, half))
        unitary, unused_factor = np.linalg.qr(random)
        gauge[sector * half:(sector + 1) * half, sector * half:(sector + 1) * half] = unitary
    transformed = np.stack([gauge.conj().T @ physical @ gauge for physical in tensor])
    rotated = TensorContractions(transformed)
    audits = []
    for positions in anchors:
        exact = targets.evaluate(positions)
        high = high_precision_target(positions)
        dense = cauchy_determinant(positions)
        observed = original.evaluate(positions)
        alternate = rotated.evaluate(positions)
        pair_errors = [abs(original.pairs[positions[end] - positions[start]]
                           / targets.pair(positions[end] - positions[start]) - 1)
                       for start, end in itertools.combinations(range(4), 2)]
        record = {"positions": positions, "exact": exact, "observed": observed,
                  "raw_relative_error": abs(observed["raw"] / exact["raw"] - 1),
                  "covariance_relative_error": abs(observed["covariance"] / exact["covariance"] - 1),
                  "all_six_pair_max_relative_error": max(pair_errors),
                  "high_precision": high, "dense_determinant": dense,
                  "dense_raw_relative_difference": abs(dense / exact["raw"] - 1),
                  "high_precision_covariance_relative_difference": abs(float(high["covariance"]) / exact["covariance"] - 1),
                  "gauge_covariance_absolute_difference": abs(alternate["covariance"] - observed["covariance"]),
                  "gauge_raw_absolute_difference": abs(alternate["raw"] - observed["raw"])}
        audits.append(record)
        if record["high_precision_covariance_relative_difference"] > 1e-10 or record["gauge_covariance_absolute_difference"] > 1e-10:
            raise RuntimeError("Focused numerical audit failed")
    validation = json.loads((ROOT / "validation_ed.json").read_text())
    summary = {"proposal_quartet_count": len(quartets),
               "proposal_failure_count_at_ten_percent": sum(record["covariance_relative_error"] > .1 for record in ranked),
               "proposal_minimum_covariance_target": min(record["exact"]["covariance"] for record in ranked),
               "proposal_raw_max_relative_error": checked["raw_max_relative_error"],
               "proposal_covariance_max_relative_error": checked["covariance_max_relative_error"],
               "original_v2_passed": checked["original_v2_passed"],
               "original_v2_headline": {key: checked["original_v2_metrics"][key] for key in
                                        ("energy_excess", "order_max_relative_error", "density_max_relative_error", "y_max_relative_error", "correlation_length")},
               "ed_quartets_checked": sum(report["quartets_checked"] for report in validation["finite_spin_ed"]),
               "ed_max_absolute_difference": max(report["maximum_absolute_difference"] for report in validation["finite_spin_ed"]),
               "ed_max_eigen_residual": max(report["residual"] for report in validation["finite_spin_ed"]),
               "audited_anchors": audits,
               "achievability_of_proposed_target": "not tested; no tensor optimization or reference portfolio was run"}
    write_json(ROOT / "focused_results.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
