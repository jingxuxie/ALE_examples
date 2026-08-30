import hashlib
import itertools
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from rebased import Benchmark, HERE, ROOT, profile, write_json
from optimize import RebasedSearch


def independent_profile(features, counts):
    support = np.flatnonzero(counts)
    rows = features[:, support] * 8
    contribution = counts[support][None, :, None, None] * rows[:, :, :, None] * rows[:, :, None, :]
    ridge = np.eye(14) * 1e-10
    right_hand_side = np.eye(14)[:, :12]
    intact_solutions = np.linalg.solve(contribution.sum(axis=1) + ridge, np.broadcast_to(right_hand_side, (len(rows), 14, 12)))
    intact = np.trace(intact_solutions[:, :12], axis1=1, axis2=2)
    worst = np.zeros(len(rows))
    for deleted in itertools.combinations(range(len(support)), 2):
        keep = np.ones(len(support), dtype=bool)
        keep[list(deleted)] = False
        information = contribution[:, keep].sum(axis=1) + ridge
        solved = np.linalg.solve(information, np.broadcast_to(right_hand_side, (len(rows), 14, 12)))
        risk = np.trace(solved[:, :12], axis1=1, axis2=2)
        if not np.all(np.isfinite(risk)) or np.any(risk <= 0):
            raise ValueError("invalid independent solve")
        worst = np.maximum(worst, risk)
    return dict(intact=intact, double=worst)


def main():
    started = time.monotonic()
    benchmark = Benchmark()
    counts = np.array(json.loads((HERE / "design.json").read_text())["batches"])
    report = dict(reference_sha256=benchmark.champion_hash,
                  candidate_sha256=hashlib.sha256((HERE / "design.json").read_bytes()).hexdigest(),
                  independent_reconstruction={})
    for label, candidate_counts in [("reference", benchmark.reference_counts), ("candidate", counts)]:
        independent = independent_profile(benchmark.features, candidate_counts)
        canonical = profile(benchmark.features, candidate_counts, direct=True)
        report["independent_reconstruction"][label] = {
            mode: float(np.max(np.abs(independent[mode] / canonical[mode] - 1))) for mode in ["intact", "double"]}
    optimizer = RebasedSearch(1, 523117)
    support = np.flatnonzero(counts)
    allocation = counts[support] * optimizer.costs[support] / optimizer.available
    state = optimizer.state(allocation, support)
    objective_errors = []
    guard_errors = []
    family_errors = []
    step = 1e-7
    for local in range(len(support)):
        changed = np.zeros(len(support))
        changed[local] = step
        plus = optimizer.state(allocation + changed, support)
        minus = optimizer.state(allocation - changed, support)
        objective_difference = (plus[0] - minus[0]) / (2 * step)
        intact_difference = (plus[2] - minus[2]) / (2 * step)
        family_difference = (plus[4] - minus[4]) / (2 * step)
        objective_errors.append(float(abs(objective_difference - state[1][local]) / max(1, abs(objective_difference))))
        guard_errors.append(float(abs(intact_difference - state[3][local]) / max(1, abs(intact_difference))))
        family_errors.append(float(np.max(abs(family_difference - state[5][:, local]) / np.maximum(1, abs(family_difference)))))
    report["analytic_gradient_max_normalized_error"] = dict(objective=max(objective_errors), intact_guard=max(guard_errors), family_guards=max(family_errors))
    protected = json.loads((HERE / "protected_hashes.json").read_text())
    changed = [path for path, expected in protected.items() if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected]
    report["protected_paths_checked"] = len(protected)
    report["protected_paths_changed"] = changed
    report["numerical_checks_passed"] = (max(value for entry in report["independent_reconstruction"].values() for value in entry.values()) < 1e-7 and
                                           max(report["analytic_gradient_max_normalized_error"].values()) < 1e-5)
    execution_ticks, distinct = benchmark.validate(counts)
    report["candidate_physically_valid"] = True
    report["execution_ticks"] = execution_ticks
    report["distinct_circuits"] = distinct
    report["elapsed_seconds"] = time.monotonic() - started
    write_json(HERE / "numerical_checks.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
