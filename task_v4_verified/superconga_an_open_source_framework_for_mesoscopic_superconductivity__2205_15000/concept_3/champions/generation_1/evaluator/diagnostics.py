import copy
import json
import math
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import bdg


def alternatives(scene):
    output = []
    occupied = {item["site"] for item in scene["impurities"]}
    for index, impurity in enumerate(scene["impurities"]):
        changed = copy.deepcopy(scene)
        changed["impurities"][index]["strength"] *= -1
        output.append(("sign", changed))
        for site in bdg.SPEC["impurity_sites"]:
            if site not in occupied:
                changed = copy.deepcopy(scene)
                changed["impurities"][index]["site"] = site
                output.append(("support", changed))
        changed = copy.deepcopy(scene)
        strength = impurity["strength"]
        magnitude = abs(strength) + (0.15 if abs(strength) <= 1.45 else -0.15)
        changed["impurities"][index]["strength"] = float(np.sign(strength) * magnitude)
        output.append(("strength", changed))
    for vortices in bdg.sectors():
        if vortices != sorted(scene["vortices"]):
            changed = copy.deepcopy(scene)
            changed["vortices"] = vortices
            output.append(("vortex", changed))
    return output


def refit(scene, actions, observations):
    support = np.asarray([item["site"] for item in scene["impurities"]])
    columns = [bdg.SPEC["impurity_sites"].index(int(site)) for site in support]
    initial = np.asarray([item["strength"] for item in scene["impurities"]])
    positive = initial >= 0
    bounds = (np.where(positive, 0.55, -1.6), np.where(positive, 1.6, -0.55))
    last_parameters = None
    cached = None

    def evaluate(parameters):
        nonlocal last_parameters, cached
        if last_parameters is not None and np.array_equal(parameters, last_parameters):
            return cached
        potential = np.zeros(64)
        potential[support] = parameters
        values, jacobian = bdg.predict_potential(potential, scene["vortices"], actions, jacobian=True)
        last_parameters = parameters.copy()
        cached = values - observations, jacobian[:, columns]
        return cached

    result = least_squares(lambda parameters: evaluate(parameters)[0], initial,
                           jac=lambda parameters: evaluate(parameters)[1], bounds=bounds,
                           max_nfev=90, ftol=1e-10, xtol=1e-10, gtol=1e-10)
    return float(np.sqrt(np.mean(result.fun ** 2)))


def episode_diagnostic(case):
    scene = case["scene"]
    truth = bdg.ldos_table(scene).ravel()
    actions = bdg.uniform_actions()
    indices = np.asarray([41 * action["site"] + action["energy_index"] for action in actions])
    candidates = alternatives(scene)
    tables = np.asarray([bdg.ldos_table(candidate).ravel() for _, candidate in candidates])
    differences = tables - truth
    uniform_rms = np.sqrt(np.mean(differences[:, indices] ** 2, axis=1))
    full_rms = np.sqrt(np.mean(differences ** 2, axis=1))
    groups = {}
    for kind in ("support", "sign", "strength", "vortex"):
        selection = np.asarray([label == kind for label, _ in candidates])
        groups[kind] = {"count": int(np.sum(selection)), "min_uniform56_rms": float(np.min(uniform_rms[selection])),
                        "min_full_grid_rms": float(np.min(full_rms[selection]))}
    discrete = [index for index, (kind, _) in enumerate(candidates) if kind in ("support", "vortex", "sign")]
    nearest = sorted(discrete, key=lambda index: uniform_rms[index])[:8]
    refitted = [{"kind": candidates[index][0], "rms": refit(candidates[index][1], actions, truth[indices])} for index in nearest]
    _, jacobian = bdg.predict_potential(bdg.potential_of(scene), scene["vortices"], actions, jacobian=True)
    support_columns = [bdg.SPEC["impurity_sites"].index(item["site"]) for item in scene["impurities"]]
    singular = np.linalg.svd(jacobian[:, support_columns], compute_uv=False)
    active = list(indices[:8])
    accumulated = np.sum(differences[:, active] ** 2, axis=1)
    available = np.ones(2624, dtype=bool)
    available[active] = False
    for _ in range(48):
        closest = np.argsort(accumulated)[:12]
        gain = np.min(accumulated[closest, None] + differences[closest] ** 2, axis=0)
        gain[~available] = -np.inf
        selected = int(np.argmax(gain))
        active.append(selected)
        available[selected] = False
        accumulated += differences[:, selected] ** 2
    return {"id": case["id"], "family": case["family"], "impurities": len(scene["impurities"]),
            "vortices": len(scene["vortices"]), "candidate_count": len(candidates), "separation": groups,
            "nearest_discrete_candidates_after_strength_refit": refitted,
            "minimum_refitted_wrong_scene_rms": min(item["rms"] for item in refitted),
            "support_jacobian_min_singular": float(singular[-1]),
            "support_jacobian_condition": float(singular[0] / singular[-1]),
            "oracle_design_min_uniform56_rms": float(np.min(uniform_rms)),
            "oracle_design_min_selected56_rms": float(np.sqrt(np.min(accumulated) / 56)),
            "oracle_design_gain": float(np.sqrt(np.min(accumulated) / 56) / np.min(uniform_rms))}


def main():
    start = time.monotonic()
    cases = json.loads((ROOT / "participant" / "input" / "calibration.json").read_text())["episodes"]
    results = []
    for case in cases:
        result = episode_diagnostic(case)
        results.append(result)
        print(json.dumps({"id": result["id"], "minimum_refitted_wrong_scene_rms": result["minimum_refitted_wrong_scene_rms"],
                          "oracle_design_gain": result["oracle_design_gain"]}), flush=True)
    support_count = sum(math.comb(36, count) for count in range(4, 8))
    report = {"scope": "public calibration only", "support_sector_combinations": 46 * support_count,
              "rounding_half_width": 5e-13, "instrument_noise_std": 0.0,
              "interpretation": "Finite local alternatives and fixed-support Jacobian only; not global identifiability or computational-solvability proof.",
              "design_caveat": "Oracle diagnostic uses the true scene to form local alternatives and maximin differences. It is not a submitted adaptive policy or evidence of a solved episode.",
              "refit_caveat": "Eight nearest wrong discrete scenes per case; local bounded strength optimization with fixed signs, not exhaustive global refitting.",
              "episodes": results, "wall_seconds": time.monotonic() - start}
    (ROOT / "attempts" / "identifiability.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
