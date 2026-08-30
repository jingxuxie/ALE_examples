import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import sys
import time


for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adversary/champion_method"))
from fit import Fit, patterns


def probe(job):
    entry, seconds = job
    target = entry["suite"]["targets"][0]
    started = time.monotonic()
    generator = np.random.default_rng(sum(map(ord, entry["id"])))
    candidates = []
    fits = 0
    for name, edges in patterns(target["n_qubits"], target["max_cnot"]).items():
        fitter = Fit(target, edges)
        initial = generator.uniform(-np.pi, np.pi, fitter.np)
        optimized = minimize(fitter.fun, initial, jac=True, method="L-BFGS-B",
                             options={"maxiter": 900, "ftol": 2e-13, "gtol": 1e-8, "maxcor": 30})
        candidates.append((float(optimized.fun), list(edges), optimized.x.copy()))
        fits += 1
        if time.monotonic() - started >= seconds:
            break
    candidates.sort(key=lambda candidate: candidate[0])
    while time.monotonic() - started < seconds and candidates[0][0] > 1e-8:
        ancestor = candidates[int(generator.integers(min(3, len(candidates))))]
        edges = list(ancestor[1])
        if generator.random() < 0.70:
            location = int(generator.integers(len(edges)))
            left = int(generator.integers(target["n_qubits"] - 1))
            edges[location] = (left, left + 1)
        else:
            first, second = generator.choice(len(edges), 2, replace=False)
            edges[first], edges[second] = edges[second], edges[first]
        fitter = Fit(target, edges)
        initial = ancestor[2].copy()
        if generator.random() < 0.4:
            initial += generator.normal(0, 0.4, len(initial))
        optimized = minimize(fitter.fun, initial, jac=True, method="L-BFGS-B",
                             options={"maxiter": 1200, "ftol": 2e-13, "gtol": 1e-8, "maxcor": 30})
        candidates.append((float(optimized.fun), edges, optimized.x.copy()))
        candidates.sort(key=lambda candidate: candidate[0])
        candidates = candidates[:5]
        fits += 1
    best = candidates[0]
    fitter = Fit(target, best[1])
    return {"id": entry["id"], "n_qubits": target["n_qubits"], "max_cnot": target["max_cnot"],
            "best_infidelity": best[0], "passed": best[0] <= 1e-8, "fits": fits,
            "elapsed_seconds": time.monotonic() - started, "statistics": entry.get("statistics", {}),
            "approximate_witness": {target["id"]: fitter.witness(best[2])}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=45)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.pool.read_text())
    entries = payload if isinstance(payload, list) else payload["cases"]
    results = []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(probe, (entry, args.seconds)) for entry in entries]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            summary = {"method": "Actual champion analytic-gradient kernel plus reconstructed topology-mutation portfolio",
                       "caution": "The submitted champion is a fixed witness, not a general solver; its failure on unrelated matrices is NOT counted as hardness. This method probe is generation-time selection evidence, not a fresh-agent attempt.",
                       "cases_completed": len(results), "passes": sum(row["passed"] for row in results),
                       "elapsed_seconds": time.monotonic() - started, "cases": results}
            args.output.write_text(json.dumps(summary, indent=2))
            print(result["id"], result["best_infidelity"], result["fits"], flush=True)


if __name__ == "__main__":
    main()
