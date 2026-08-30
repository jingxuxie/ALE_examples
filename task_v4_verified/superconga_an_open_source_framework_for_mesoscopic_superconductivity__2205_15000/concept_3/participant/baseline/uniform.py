import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))

import numpy as np
from scipy.optimize import least_squares

import bdg


class TimeLimit(Exception):
    pass


def fit(actions, observations, seconds=78.0):
    deadline = time.monotonic() + seconds
    observations = np.asarray(observations)
    allowed = np.asarray(bdg.SPEC["impurity_sites"])
    regularization = 0.00008
    smoothing = 0.04
    candidates = []
    best = None
    diagnostics = {"dense_fits": 0, "sparse_fits": 0}

    def optimize(vortices, initial, support=None, evaluations=30):
        last_parameters = None
        last_result = None

        def evaluate(parameters):
            nonlocal last_parameters, last_result
            if time.monotonic() > deadline:
                raise TimeLimit()
            if last_parameters is not None and np.array_equal(parameters, last_parameters):
                return last_result
            potential = np.zeros(64)
            selected = np.arange(36) if support is None else np.asarray(support)
            potential[allowed[selected]] = parameters
            values, gradient = bdg.predict_potential(potential, vortices, actions, jacobian=True)
            residual = values - observations
            gradient = gradient[:, selected]
            if support is None:
                root = parameters ** 2 + smoothing ** 2
                penalty = np.sqrt(regularization) * root ** 0.25
                derivative = np.sqrt(regularization) * 0.5 * parameters * root ** -0.75
                residual = np.concatenate((residual, penalty))
                gradient = np.vstack((gradient, np.diag(derivative)))
            last_parameters = parameters.copy()
            last_result = residual, gradient
            return last_result

        if support is None:
            bounds = (-1.6, 1.6)
        else:
            signs = np.where(initial >= 0, 1.0, -1.0)
            bounds = (np.where(signs > 0, 0.55, -1.6), np.where(signs > 0, 1.6, -0.55))
            initial = np.clip(initial, bounds[0] + 1e-8, bounds[1] - 1e-8)
        result = least_squares(lambda parameters: evaluate(parameters)[0], initial,
                               jac=lambda parameters: evaluate(parameters)[1], bounds=bounds,
                               max_nfev=evaluations, ftol=1e-7, xtol=1e-7, gtol=1e-7)
        return result.x, float(np.sum(evaluate(result.x)[0] ** 2))

    try:
        for vortices in bdg.sectors():
            parameters, objective = optimize(vortices, np.zeros(36), evaluations=24)
            candidates.append((objective, vortices, parameters))
            diagnostics["dense_fits"] += 1
        candidates.sort(key=lambda candidate: candidate[0])
        refined = []
        for _, vortices, parameters in candidates[:6]:
            parameters, objective = optimize(vortices, parameters, evaluations=70)
            refined.append((objective, vortices, parameters))
        refined.sort(key=lambda candidate: candidate[0])
        for _, vortices, dense in refined[:4]:
            for count in range(bdg.SPEC["impurity_count"][0], bdg.SPEC["impurity_count"][1] + 1):
                support = np.argsort(abs(dense))[-count:]
                parameters, objective = optimize(vortices, dense[support], support, evaluations=70)
                diagnostics["sparse_fits"] += 1
                if best is None or objective < best[0]:
                    best = (objective, list(vortices), support.copy(), parameters.copy())
    except TimeLimit:
        diagnostics["time_limited"] = True
    if best is None:
        if candidates:
            _, vortices, parameters = min(candidates, key=lambda candidate: candidate[0])
        else:
            vortices, parameters = [], np.ones(36)
        support = np.argsort(abs(parameters))[-bdg.SPEC["impurity_count"][0]:]
        selected = parameters[support]
        selected = np.where(selected >= 0, 1, -1) * np.clip(abs(selected), 0.55, 1.6)
        best = (float("inf"), vortices, support, selected)
    objective, vortices, support, parameters = best
    diagnostics["residual_sum_squares"] = objective if np.isfinite(objective) else None
    scene = {"impurities": [{"site": int(allowed[index]), "strength": float(strength)}
                             for index, strength in zip(support, parameters)], "vortices": vortices}
    return bdg.validate_scene(scene), diagnostics


def main():
    metadata = json.loads(sys.stdin.readline())
    if metadata.get("protocol") != "ldos-jsonl-v1":
        raise ValueError("unsupported protocol")
    actions = bdg.uniform_actions(metadata["model"]["query_budget"])
    observations = []
    for action in actions:
        print(json.dumps(action), flush=True)
        observation = json.loads(sys.stdin.readline())
        if observation.get("type") != "observation":
            raise ValueError("expected observation")
        observations.append(observation["value"])
    scene, diagnostics = fit(actions, observations)
    print(json.dumps({"type": "final", "estimate": scene}, allow_nan=False), flush=True)
    print(json.dumps(diagnostics, allow_nan=False), file=sys.stderr)


if __name__ == "__main__":
    main()
