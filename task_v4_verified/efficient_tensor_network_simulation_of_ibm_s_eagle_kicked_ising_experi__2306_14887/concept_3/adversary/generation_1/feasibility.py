import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from physics import HERE, ROOT, OLD_SCALE, champion, exact, fast, row_to_scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--iterations", type=int, default=260)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--label", default="drift_001")
    parser.add_argument("--exchange-cases", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    prior_worst = np.load(ROOT / "champions" / "generation_1" / "worst_errors.npy", allow_pickle=False)[0]
    bases = [np.zeros(15), prior_worst]
    for signs in itertools.product((-1, 1), repeat=3):
        bases.append(np.r_[np.asarray(signs) * OLD_SCALE[:3], np.full(12, signs[2] * 0.005)])
    rows = [np.r_[base, np.zeros(12)] for base in bases]
    rows.extend(np.r_[base, np.full(12, args.amplitude)] for base in bases)
    for pattern in ((-1.0) ** np.arange(12), np.r_[np.ones(6), -np.ones(6)],
                    1 - 2 * np.asarray([0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0]),
                    np.cos(2 * np.pi * np.arange(12) / 12)):
        rows.append(np.r_[np.zeros(15), args.amplitude * pattern])
        rows.append(np.r_[prior_worst, args.amplitude * pattern])
    if args.exchange_cases:
        archive = np.load(HERE / "boundary_drift_cases.npz", allow_pickle=False)
        additional = archive["scenarios"][np.argsort(archive["fidelities"])[:6]].copy()
        additional[:, 15:] *= args.amplitude / 0.01
        rows.extend(additional)
    scenarios = np.asarray(rows)
    if args.resume:
        controls = np.asarray(json.loads(args.resume.read_text())["angles"]).reshape(-1)
    else:
        controls = champion().reshape(-1)
    checkpoint = HERE / (args.label + "_private_candidate.json")
    counter = 0
    best = -1.0
    history = []
    def objective(angles):
        nonlocal counter, best
        scores, gradients = fast(angles, scenarios, gradients=True)
        temperature = 0.002
        normalizer = logsumexp(-scores / temperature)
        weights = np.exp(-scores / temperature - normalizer)
        minimum = float(scores.min())
        counter += 1
        if minimum > best:
            best = minimum
            checkpoint.write_text(json.dumps({"schema_version": 1, "angles": angles.reshape(24, 2).tolist()}, indent=2) + "\n")
        if counter % 25 == 0:
            record = {"evaluations": counter, "minimum": minimum, "mean": float(scores.mean()),
                      "best_minimum": best, "seconds": time.monotonic() - started}
            history.append(record)
            print(json.dumps(record), flush=True)
            (HERE / (args.label + "_progress.json")).write_text(json.dumps(history, indent=2) + "\n")
        return temperature * normalizer, -weights @ gradients
    result = minimize(objective, controls, jac=True, method="L-BFGS-B", bounds=[(-np.pi, np.pi)] * 48,
                      options={"maxiter": args.iterations, "ftol": 2e-12, "gtol": 1e-7, "maxls": 25})
    controls = np.asarray(json.loads(checkpoint.read_text())["angles"])
    scores, _ = fast(controls, scenarios)
    worst = int(np.argmin(scores))
    independent = exact(controls, scenarios[worst])
    report = {"proposed_model_only": True, "drift_bound": args.amplitude, "training_scenarios": len(scenarios),
              "training_minimum": float(scores.min()), "independent_worst": independent,
              "worst_scenario": row_to_scenario(scenarios[worst]), "iterations": int(result.nit),
              "evaluations": counter, "seconds": time.monotonic() - started,
              "training_target_passed": float(scores.min()) >= 0.95,
              "not_a_frozen_generation_2_task": True, "not_a_continuum_certificate": True}
    (HERE / (args.label + "_feasibility.json")).write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(HERE / (args.label + "_training.npz"), scenarios=scenarios, fidelities=scores)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
