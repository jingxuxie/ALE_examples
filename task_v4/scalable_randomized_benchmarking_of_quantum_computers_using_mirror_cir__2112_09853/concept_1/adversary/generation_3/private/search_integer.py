import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import qr

PRIVATE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRIVATE_ROOT / "ratchet2"))
from integer_repair_search import family_repairs, integer_projection
from model import GeneralModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=180)
    arguments = parser.parse_args()
    started = time.perf_counter()
    deadline = started + arguments.seconds
    model = GeneralModel()
    family_means = np.zeros((256, 192))
    selected = model.error_gate < 24
    family_means[model.error_label[selected], np.flatnonzero(selected)] = 1
    model.full_constraint = np.vstack((model.full_constraint, family_means[1:]))
    model.full_target = model.full_constraint @ model.uniform
    model.integer_target = np.rint(60 * model.full_target).astype(int)
    _, triangular, _ = qr(model.full_constraint.T, pivoting=True, mode="economic")
    rank = int(np.sum(abs(np.diag(triangular)) > 1e-10))
    source_path = PRIVATE_ROOT / "ratchet2" / "family_means_pairs_search.json"
    source = json.loads(source_path.read_text())["result"]
    starts = sorted((run for run in source["runs"] if run["success"]), key=lambda run: -run["metrics"]["bias"])
    single_quadratic = model.quadratic.copy()
    single_quadratic[72:, :] = 0
    single_quadratic[:, 72:] = 0
    cx_quadratic = (model.quadratic - single_quadratic) // 2
    generator = np.random.default_rng(235)
    seen = set()
    progress = []
    evaluated = 0
    lp_nodes = 0
    for attempt in range(500):
        if time.perf_counter() >= deadline:
            break
        source_run = starts[attempt % len(starts)]
        point = 60 * np.array(source_run["conditional"])
        counts, nodes = integer_projection(model, point, generator, deadline, randomized=attempt >= len(starts))
        lp_nodes += nodes
        if counts is None or tuple(counts) in seen:
            continue
        seen.add(tuple(counts))
        gradient = model.run(point / 60, gradient=True)[1]
        single_options, single_stats = family_repairs(model, counts, single_quadratic, "single", 28800, gradient)
        cx_options, cx_stats = family_repairs(model, counts, cx_quadratic, "cx", 1920, gradient)
        row = {"attempt": attempt, "source_start": source_run["start"], "lp_nodes": nodes,
               "single_repairs": single_stats, "cx_repairs": cx_stats}
        progress.append(row)
        print(json.dumps(row), flush=True)
        combinations = sorted(((single_cost + cx_cost, single_change, cx_change)
                               for single_cost, single_change in single_options
                               for cx_cost, cx_change in cx_options), key=lambda entry: entry[0])
        for _, single_change, cx_change in combinations[:256]:
            if time.perf_counter() >= deadline:
                break
            candidate = counts + single_change + cx_change
            if not np.array_equal(model.full_constraint @ candidate, model.integer_target):
                raise AssertionError("Native-family mean calibration changed")
            if int(candidate @ single_quadratic @ candidate) != 28800 or int(candidate @ cx_quadratic @ candidate) != 1920:
                raise AssertionError("Native-family pair calibration changed")
            metrics = model.run(candidate / 60, scan=True)
            evaluated += 1
            if metrics["bias"] >= 0.0235 and metrics["max_residual"] <= 0.004 and metrics["end_signal"] >= 0.005:
                result = {"found": True, "target": 0.0235, "elapsed_seconds": time.perf_counter() - started,
                          "deadline_seconds": arguments.seconds, "linear_rank": rank,
                          "source": str(source_path), "source_start": source_run["start"],
                          "lp_nodes": lp_nodes, "integer_projections": len(seen), "exact_candidates_evaluated": evaluated,
                          "metrics": {name: value for name, value in metrics.items() if name != "polarizations"},
                          "family_calibrations": model.family_calibrations(candidate),
                          "witness": model.encode(candidate), "progress": progress}
                print("FINAL_JSON " + json.dumps(result, allow_nan=False), flush=True)
                return
    print("FINAL_JSON " + json.dumps({"found": False, "target": 0.0235,
                                      "elapsed_seconds": time.perf_counter() - started, "linear_rank": rank,
                                      "lp_nodes": lp_nodes, "integer_projections": len(seen),
                                      "exact_candidates_evaluated": evaluated, "progress": progress}), flush=True)


if __name__ == "__main__":
    main()
