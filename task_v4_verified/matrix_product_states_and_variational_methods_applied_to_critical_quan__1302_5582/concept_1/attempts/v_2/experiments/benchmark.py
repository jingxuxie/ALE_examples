import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from contractor import measure, save_mps
from optimizer import optimize
from mps import product_state, sweep, make_mpo, project_parity


def make_case(name, length, dimension, cap, sector, mass, quartic, omega, coupling):
    return dict(version=1, case_id=name, seed=123, n_sites=length, local_dim=dimension,
                bond_cap=cap, sector=sector, mass2=[mass] * length,
                lambda4=[quartic] * length, omega=[omega] * length,
                coupling=[coupling] * (length - 1), field=[0.0] * length,
                budget_seconds=6.0, wall_seconds=120.0)


def cases():
    result = [make_case("large_sym", 22, 14, 12, "even", 0.6, 2.0, 0.55, 1.5),
              make_case("large_odd", 22, 14, 12, "odd", 0.2, 1.2, 1.85, 1.5),
              make_case("cross_even", 20, 12, 10, "even", -0.7, 2.0, 0.8, 1.0),
              make_case("cross_odd", 18, 14, 8, "odd", -0.5, 2.8, 0.55, 1.2),
              make_case("deep_even", 22, 14, 12, "even", -2.8, 1.2, 0.55, 1.5),
              make_case("deep_odd", 16, 12, 6, "odd", -2.5, 2.8, 1.85, 0.7),
              make_case("interface", 22, 14, 12, "any", -1.5, 1.5, 1.0, 1.0),
              make_case("weak_link", 20, 12, 10, "any", -0.8, 2.0, 1.0, 1.0)]
    rng = np.random.default_rng(444)
    for request in result[-2:]:
        length = request["n_sites"]
        request["mass2"] = np.linspace(-2.2, 0.6, length).tolist()
        request["omega"] = rng.uniform(0.55, 1.85, length).tolist()
        request["coupling"][length // 2] = 0.06
        request["field"] = rng.uniform(-0.004, 0.004, length).tolist()
    return result


if __name__ == "__main__":
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    mode = sys.argv[2] if len(sys.argv) > 2 else "new"
    results = []
    for request in cases():
        request["budget_seconds"] = budget
        Path("experiments/" + request["case_id"] + ".json").write_text(json.dumps(request))
        start = time.process_time()
        if mode == "baseline":
            tensors = sweep(product_state(request, tilt=0.12), make_mpo(request), 2,
                            tolerance=1e-3, maxiter=10, deadline=start + 0.4 * budget)
            tensors = project_parity(tensors, request["sector"])
        else:
            tensors = optimize(request, start - 0.2, time.monotonic())
        elapsed = time.process_time() - start
        metrics = measure(tensors, request)
        save_mps("experiments/" + request["case_id"] + "_" + mode + str(int(budget)) + ".npz", tensors)
        result = dict(case=request["case_id"], cpu=elapsed, **metrics)
        print(json.dumps(result), flush=True)
        results.append(result)
    Path("experiments/results_" + mode + str(int(budget)) + ".json").write_text(json.dumps(results, indent=2))
