import sys

sys.dont_write_bytecode = True

import copy
import json
from pathlib import Path
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

from cases import cases
from run import check_frozen
from validation_model import characters, walsh


ROOT = Path(__file__).resolve().parent


def projection(spec):
    dimension = spec["detector_count"]
    original = np.array([channel["masks"] for channel in spec["channels"]], dtype=np.int64)
    unique_masks = np.unique(original)
    rng = np.random.default_rng(19431)
    for attempt in range(64):
        codes = np.left_shift(np.int64(1), np.arange(dimension, dtype=np.int64))
        for iteration in range(10 * dimension):
            first, second = rng.choice(dimension, 2, replace=False)
            codes[first] ^= codes[second]
        projected = np.zeros(len(unique_masks), dtype=np.int64)
        for detector in range(dimension):
            projected ^= ((unique_masks >> detector) & 1) * codes[detector]
        projected &= (1 << min(14, dimension)) - 1
        if len(np.unique(projected)) == len(unique_masks) and np.all(projected):
            break
    result = np.zeros_like(original)
    for detector in range(dimension):
        result ^= ((original >> detector) & 1) * codes[detector]
    return result, len(np.unique(projected)) == len(unique_masks) and bool(np.all(projected))


def information(case, bits):
    spec = copy.deepcopy(case["spec"])
    mapped, distinct = projection(spec)
    state_count = 1 << bits
    for channel, masks in zip(spec["channels"], mapped):
        channel["masks"] = (masks & (state_count - 1)).tolist()
    spec["detector_count"] = bits
    point = np.log(case["rates"])
    matrices = []
    maximum_normalization_error = 0.0
    started = time.process_time()
    for action in range(len(spec["actions"])):
        means, derivatives = [], []
        for start in range(0, state_count, 512):
            mean, derivative = characters(spec, point, action, np.arange(start, min(start + 512, state_count)), True)
            means.append(mean)
            derivatives.append(derivative)
        probability = walsh(np.concatenate(means)) / state_count
        derivative = walsh(np.concatenate(derivatives).T) / state_count
        maximum_normalization_error = max(maximum_normalization_error, abs(probability.sum() - 1.0), float(np.max(np.abs(derivative.sum(axis=1)))))
        probability = np.maximum(probability, 1e-15)
        matrices.append((derivative / probability[None, :]) @ derivative.T)
    matrices = np.array(matrices)
    families = np.array([channel["family"] for channel in spec["channels"]])
    groups = np.array([families == family for family in sorted(set(families))], dtype=float)
    groups /= groups.sum(axis=1, keepdims=True)

    def summarize(weights):
        matrix = np.einsum("a,aij->ij", weights * spec["shot_budget"], matrices)
        covariance = np.linalg.inv(matrix)
        standard = np.sqrt(groups @ np.diag(covariance))
        return {"mean_family_log_sd": float(standard.mean()), "max_family_log_sd": float(standard.max()),
                "family_log_sd": dict(zip(sorted(set(families)), standard.tolist())),
                "rank": int(np.linalg.matrix_rank(matrix)), "minimum_eigenvalue": float(np.linalg.eigvalsh(matrix)[0])}

    def objective(weights):
        matrix = np.einsum("a,aij->ij", weights * spec["shot_budget"], matrices) + np.eye(len(point)) * 1e-8
        covariance = cho_solve(cho_factor(matrix, lower=True), np.eye(len(point)))
        standard = np.sqrt(groups @ np.diag(covariance))
        diagonal = (1.0 / (2 * standard)) @ groups
        sensitivity = (covariance * diagonal[None, :]) @ covariance
        gradient = -spec["shot_budget"] * np.einsum("ij,aji->a", sensitivity, matrices)
        return float(standard.mean()), gradient / len(standard)

    uniform = np.full(len(matrices), 1.0 / len(matrices))
    optimum = minimize(objective, uniform, jac=True, method="SLSQP", bounds=[(0.0, 1.0)] * len(matrices),
                       constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1.0},
                       options={"maxiter": 80, "ftol": 1e-9})
    allocation = np.maximum(optimum.x, 1e-9)
    allocation /= allocation.sum()
    return {"case": case["id"], "detectors": case["spec"]["detector_count"], "projection_bits": bits,
            "channels": len(point), "unique_nonzero_single_footprints": distinct,
            "uniform_fisher": summarize(uniform), "true_rate_optimal_allocation_fisher": summarize(allocation),
            "normalization_error": maximum_normalization_error, "parent_diagnostic_cpu_seconds": time.process_time() - started,
            "warning": "Exact full projected-outcome Fisher, not merely a few parity means. True-rate optimized allocation is only an information diagnostic, not a latent-blind policy or finite-sample qualification. Width-corrected public projection construction is independently implemented; participant code is never imported."}


def main():
    check_frozen()
    results = []
    for bits in (14, 16):
        for case in cases(seed=49371023, sizes=(28, 44), topologies=("triangular",)):
            result = information(case, bits)
            results.append(result)
            (ROOT / "selected_projection_information.json").write_text(json.dumps({"results": results, "targets": None}, indent=2) + "\n")
            print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
