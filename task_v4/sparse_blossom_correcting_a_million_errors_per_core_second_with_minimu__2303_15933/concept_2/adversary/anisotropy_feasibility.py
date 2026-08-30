import sys

sys.dont_write_bytecode = True

import argparse
import ctypes
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize

import extension_stress as extension


def fields():
    projection = extension.projection_matrix()
    orientation = np.asarray([1] * 24 + [-1] * 15)
    base = []
    for count, family in ((4, "rows"), (5, "columns")):
        for tail in itertools.product((-1, 1), repeat=count - 1):
            if min(tail) == 1:
                continue
            signs = [1, *tail]
            field = [signs[detector % 4 if family == "rows" else detector // 4] for detector in range(20)]
            base.append(projection @ field)
    new = [orientation]
    new.extend(orientation * raw for raw in base)
    for row in range(4):
        for column in range(5):
            field = [(1 - 2 * int(detector % 4 == row)) * (1 - 2 * int(detector // 4 == column)) for detector in range(20)]
            new.append(orientation * (projection @ field))
    return np.asarray(base + new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=240)
    parser.add_argument("--seed", type=int, default=3107)
    arguments = parser.parse_args()
    library = ctypes.CDLL(str(extension.PRIVATE / "anisotropy_feasibility.so"))
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.batch_metrics.argtypes = [pointer, ctypes.c_int, ctypes.c_uint, pointer]
    library.batch_metrics.restype = None
    raw = fields()
    background = np.asarray([0.95, 1.05])
    parameters = np.asarray([-0.05, 0, 0.05])
    row_radius = np.asarray([0.001] * 22 + [0.00125] * 43)
    nominal = json.loads((extension.CONCEPT / "champions/generation_2/witness.json").read_text())
    known = json.loads((extension.PRIVATE / "known_witness.json").read_text())
    rng = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    best_score = -math.inf
    calls = 0
    restarts = 0
    current_syndrome = nominal["syndrome"]
    best_artifact = nominal

    def constraints(vector):
        nonlocal calls
        rates = vector[:39]
        centered = raw - (raw @ rates / sum(rates))[:, None]
        direction = centered / np.max(np.abs(centered), axis=1)[:, None]
        local = background[None, :, None, None] * rates[None, None, None, :] * (1 + parameters[None, None, :, None] * direction[:, None, None, :])
        global_rates = np.asarray([0.95, 1, 1.05])[:, None] * rates
        matrix = np.ascontiguousarray(np.concatenate([global_rates, local.reshape(-1, 39)]))
        result = np.empty((len(matrix), 3))
        library.batch_metrics(matrix, len(matrix), sum(1 << detector for detector in current_syndrome), result)
        calls += 1
        global_allowance = (39 / 0.95 + sum(rates / (1 - 1.05 * rates))) * 0.0025 + 1e-10
        bound = np.sum(np.abs(direction[:, None, :]) / ((1 - 0.05 * np.abs(direction[:, None, :])) * (1 - background[None, :, None] * rates * (1 + 0.05 * np.abs(direction[:, None, :])))), axis=2)
        allowance = np.concatenate([np.full(3, global_allowance), np.repeat((bound * row_radius[:, None] + 1e-10).reshape(-1), 3)])
        result -= allowance[:, None]
        target_gap = np.concatenate([np.full(3, 1.08), np.full(len(matrix) - 3, 0.85)])
        target_odds = np.concatenate([np.full(3, math.log(0.85 / 0.15)), np.full(len(matrix) - 3, math.log(0.845 / 0.155))])
        scores = np.stack([result[:, 0] / target_gap, result[:, 1] / target_odds, np.exp(result[:, 2]) / 0.0000175], axis=1)
        return np.concatenate([(scores - vector[39]).ravel(), [100 * (0.085 - np.mean(rates)), 100 * (np.std(rates) - 0.015)]])

    while time.monotonic() - started < arguments.seconds:
        restarts += 1
        seed = nominal if restarts == 1 else known if restarts == 2 else best_artifact
        current_syndrome = seed["syndrome"]
        rates = np.asarray(seed["probabilities"])
        if restarts > 2:
            rates = np.clip(rates + rng.normal(0, 0.004 if restarts % 3 else 0.025, 39), 0.02, 0.14)
        initial = np.r_[rates, 0.8]
        solution = minimize(lambda vector: -vector[39], initial, method="SLSQP", bounds=[(0.02, 0.14)] * 39 + [(0, 1.5)],
                            constraints={"type": "ineq", "fun": constraints}, options={"maxiter": 100, "ftol": 2e-9, "eps": 2e-7})
        achieved = float(min(constraints(solution.x)[:-2]) + solution.x[39])
        print(json.dumps({"restart": restarts, "score": achieved, "success": bool(solution.success), "message": solution.message, "calls": calls, "seconds": time.monotonic() - started}), flush=True)
        if achieved > best_score and np.mean(solution.x[:39]) <= 0.085 + 1e-10:
            best_score = achieved
            best_artifact = {"version": 1, "probabilities": solution.x[:39].tolist(), "syndrome": current_syndrome}
            (extension.PRIVATE / "anisotropy_candidate.json").write_text(json.dumps(best_artifact, indent=2) + "\n")
            (extension.PRIVATE / "anisotropy_search_report.json").write_text(json.dumps({"private_only": True, "score_surrogate": achieved, "certified": False, "seconds": time.monotonic() - started, "calls": calls, "restarts": restarts}, indent=2) + "\n")
        if best_score > 1.001:
            break


if __name__ == "__main__":
    main()
