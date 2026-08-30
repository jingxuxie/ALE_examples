import itertools
import json
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from physics import HERE, champion, confirm, fast


def main():
    started = time.monotonic()
    controls = champion()
    archives = [np.load(HERE / name) for name in
                ("static_recheck.npz", "matching_broad.npz", "spatial_phase_cases.npz",
                 "continuous_candidates.npz")]
    rows = np.concatenate([archive["scenarios"] for archive in archives])
    values = np.concatenate([archive["fidelities"] for archive in archives])
    selected = []
    for index in np.argsort(values):
        if all(np.max(np.abs(rows[index] - rows[previous])) > 0.012 for previous in selected):
            selected.append(index)
        if len(selected) == 8:
            break
    different = np.flatnonzero(np.max(np.abs(rows[:, 15:27] - rows[:, 27:39]), axis=1) > 0.015)
    selected.extend(different[np.argsort(values[different])[:4]].tolist())
    training = np.unique(np.r_[rows[selected], np.zeros((1, 39))], axis=0)
    branches = []
    candidates = []
    original_nominal = float(fast(controls, [np.zeros(39)])[0][0])
    for pattern in itertools.product((0, 1), repeat=4):
        candidate = controls.copy()
        for layer in range(24):
            if pattern[layer % 4]:
                candidate[layer] += np.where(candidate[layer] >= 0, -np.pi, np.pi)
        scores = fast(candidate, training)[0]
        nominal = float(fast(candidate, [np.zeros(39)])[0][0])
        branches.append({"period_four_mask": list(pattern), "training_minimum": float(scores.min()),
                         "nominal_fidelity": nominal, "nominal_invariance_error": abs(nominal - original_nominal)})
        candidates.append(candidate)
    nontrivial = max(range(1, len(branches)), key=lambda index: branches[index]["training_minimum"])
    print(json.dumps({"branch_screen": branches, "best_nontrivial": nontrivial}), flush=True)
    refinements = []
    for label, initial in (("unmodified_champion", controls),
                           ("best_nontrivial_period_four_branch", candidates[nontrivial])):
        def objective(flat):
            scores, gradients = fast(flat, training, gradients=True)
            temperature = 0.001
            weights = np.exp(-scores / temperature - logsumexp(-scores / temperature))
            return float(temperature * logsumexp(-scores / temperature)), -weights @ gradients

        result = minimize(objective, initial.reshape(48), jac=True, method="L-BFGS-B",
                          bounds=[(-np.pi, np.pi)] * 48,
                          options={"maxiter": 35, "ftol": 1e-11, "gtol": 1e-7, "maxls": 12})
        candidate = result.x.reshape(24, 2)
        artifact = HERE / ("private_variant_" + label + ".json")
        artifact.write_text(json.dumps({"angles": candidate.tolist()}, indent=2) + "\n")
        validation = fast(candidate, rows)[0]
        worst = int(np.argmin(validation))
        record = {"label": label, "training_cases": len(training), "iterations": int(result.nit),
                  "evaluations": int(result.nfev), "training_minimum": float(fast(candidate, training)[0].min()),
                  "validation_cases": len(rows), "validation_minimum": float(validation.min()),
                  "below_095": int(np.sum(validation < 0.95)),
                  "artifact": artifact.name, "max_angle": float(np.max(np.abs(candidate))),
                  "independent_worst": confirm(candidate, rows[worst], validation[worst], label),
                  "not_a_continuum_certificate": True}
        refinements.append(record)
        np.savez_compressed(HERE / ("private_variant_scores_" + label + ".npz"), fidelities=validation)
        print(json.dumps({"variant": label, "minimum": record["validation_minimum"],
                          "seconds": time.monotonic() - started}), flush=True)
    report = {"private_only": True, "training_cases": len(training), "branch_screen": branches,
              "best_nontrivial_branch_index": nontrivial, "refinements": refinements,
              "seconds": time.monotonic() - started,
              "interpretation": "Bounded exploratory comparison, not an exhaustive control search or continuum certificate."}
    (HERE / "variant_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
