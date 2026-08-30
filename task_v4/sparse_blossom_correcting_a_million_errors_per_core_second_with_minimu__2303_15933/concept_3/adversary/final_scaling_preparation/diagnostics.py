import sys

sys.dont_write_bytecode = True

import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from cases import cases
from run import check_frozen
from science_helpers import validate_case
from validation_model import characters


ROOT = Path(__file__).resolve().parent


def selected_information(case, masks):
    spec = case["spec"]
    point = np.log(case["rates"])
    xor_masks, inverse = np.unique((masks[:, None] ^ masks[None, :]).ravel(), return_inverse=True)
    matrix = np.zeros((len(point), len(point)))
    derivative_norms = []
    contrasts = []
    started = time.process_time()
    for action in range(len(spec["actions"])):
        mean, derivative = characters(spec, point, action, masks, gradient=True)
        xor_means = np.concatenate([characters(spec, point, action, xor_masks[start:start + 256])
                                    for start in range(0, len(xor_masks), 256)])
        covariance = xor_means[inverse].reshape(len(masks), len(masks)) - np.outer(mean, mean)
        transformed = cho_solve(cho_factor(covariance, lower=True), derivative)
        matrix += derivative.T @ transformed * spec["shot_budget"] / len(spec["actions"])
        derivative_norms.append(float(np.linalg.norm(derivative)))
        contrasts.append(float(np.median(np.abs(mean))))
    eigenvalues = np.linalg.eigvalsh(matrix)
    diagonal = np.diag(np.linalg.inv(matrix))
    assert np.all(diagonal > 0)
    families = np.array([channel["family"] for channel in spec["channels"]])
    family_sd = {family: float(np.sqrt(np.mean(diagonal[families == family]))) for family in sorted(set(families))}
    return {"feature_count": len(masks), "mean_feature_support": float(np.mean([int(mask).bit_count() for mask in masks])),
            "information_rank": int(np.linalg.matrix_rank(matrix)), "minimum_information_eigenvalue": float(eigenvalues[0]),
            "condition_number": float(eigenvalues[-1] / eigenvalues[0]), "uniform_40000_asymptotic_family_log_sd": family_sd,
            "mean_family_log_sd": float(np.mean(list(family_sd.values()))), "max_family_log_sd": max(family_sd.values()),
            "action_median_parity_contrast": contrasts, "action_log_rate_jacobian_frobenius": derivative_norms,
            "diagnostic_parent_cpu_seconds": time.process_time() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("geometry", "information"), required=True)
    arguments = parser.parse_args()
    check_frozen()
    results = []
    sizes = (28, 36, 44) if arguments.mode == "geometry" else (28, 44)
    for case in cases(seed=49371023, sizes=sizes):
        if arguments.mode == "geometry":
            result = validate_case(case, information=False)
        else:
            spec = case["spec"]
            local_masks = set(1 << detector for detector in range(spec["detector_count"]))
            local_masks.update(mask for channel in spec["channels"] for mask in channel["masks"])
            local_masks = np.array(sorted(local_masks), dtype=np.int64)
            rng = np.random.default_rng(137641 + spec["detector_count"])
            dense_masks = set()
            while len(dense_masks) < len(local_masks):
                dense_masks.add(int(rng.integers(1, 1 << spec["detector_count"])))
            dense_masks = np.array(sorted(dense_masks), dtype=np.int64)
            local = selected_information(case, local_masks)
            dense = selected_information(case, dense_masks)
            result = {"case": case["id"], "detectors": spec["detector_count"], "channels": len(spec["channels"]),
                      "actions": len(spec["actions"]), "local_selected_moments": local, "random_global_marginal_moments": dense,
                      "global_to_local_mean_log_sd_ratio": dense["mean_family_log_sd"] / local["mean_family_log_sd"]}
        results.append(result)
        report = {"status": "private_preparation_only", "new_generation": False, "targets": None, "cases": results,
                  "mode": arguments.mode, "hypothesis_not_champion_audit": True,
                  "limitations": "Information uses exact cross-feature/shared-mode covariance of selected empirical parity MEANS, not full likelihood or raw joint parity samples. A sufficiently large invertible binary sketch can retain all raw syndrome information. These local asymptotic diagnostics do not prove finite-budget achievability or impossibility."}
        (ROOT / (arguments.mode + ".json")).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
