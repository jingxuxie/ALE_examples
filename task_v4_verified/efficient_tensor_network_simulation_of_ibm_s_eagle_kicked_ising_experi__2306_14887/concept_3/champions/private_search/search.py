import argparse
import ctypes
import itertools
import json
import os
from pathlib import Path
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

HERE = Path(__file__).resolve().parent
LIBRARY = ctypes.CDLL(str(HERE / "adjoint.so"))
POINTER = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
LIBRARY.fidelity_gradient.argtypes = [POINTER, POINTER, ctypes.c_int, POINTER, POINTER]
LIBRARY.fidelity_gradient.restype = None


def evaluate(controls, scenarios):
    controls = np.ascontiguousarray(controls, dtype=np.float64).reshape(-1)
    scenarios = np.ascontiguousarray(scenarios, dtype=np.float64).reshape(-1, 14)
    fidelities = np.zeros(len(scenarios))
    gradients = np.zeros((len(scenarios), 48))
    LIBRARY.fidelity_gradient(controls, scenarios, len(scenarios), fidelities, gradients)
    return fidelities, gradients


def training_scenarios():
    rows = [np.zeros(14)]
    for gain_a, gain_b, zz_gain in itertools.product((-0.025, 0.025), (-0.025, 0.025), (-0.015, 0.015)):
        rows.append(np.r_[gain_a, gain_b, np.full(12, zz_gain)])
    return np.asarray(rows)


def optimize(initial, scenarios, iterations, temperature, tied=False):
    def objective(controls):
        expanded = np.repeat(controls, 2) if tied else controls
        fidelities, gradients = evaluate(expanded, scenarios)
        if tied:
            gradients = gradients.reshape(len(scenarios), 24, 2).sum(axis=2)
        weights = np.exp(-fidelities / temperature - logsumexp(-fidelities / temperature))
        return temperature * logsumexp(-fidelities / temperature), -weights @ gradients
    return minimize(objective, initial, jac=True, method="L-BFGS-B", bounds=[(-np.pi, np.pi)] * len(initial),
                    options={"maxiter": iterations, "ftol": 2e-12, "gtol": 1e-7, "maxls": 30})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--starts", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=350)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--robust", action="store_true")
    parser.add_argument("--global-kicks", action="store_true")
    parser.add_argument("--seed", type=int, default=148873)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--label", default="search")
    args = parser.parse_args()
    generator = np.random.default_rng(args.seed)
    scenarios = training_scenarios() if args.robust else np.zeros((1, 14))
    started = time.monotonic()
    best = -1.0
    records = []
    if args.resume:
        initial = np.array(json.loads(args.resume.read_text())["angles"]).reshape(-1)
    for restart in range(args.starts):
        if not args.resume:
            initial = generator.uniform(-np.pi, np.pi, 24 if args.global_kicks else 48) * args.scale
        elif restart:
            initial = np.clip(initial + generator.normal(0, 0.08, 48), -np.pi, np.pi)
        result = optimize(initial, scenarios, args.iterations, 0.015, args.global_kicks)
        expanded = np.repeat(result.x, 2) if args.global_kicks else result.x
        fidelities, _ = evaluate(expanded, scenarios)
        score = float(fidelities.min())
        record = {"restart": restart, "minimum": score, "mean": float(fidelities.mean()),
                  "nit": int(result.nit), "nfev": int(result.nfev), "seconds": time.monotonic() - started}
        records.append(record)
        print(json.dumps(record), flush=True)
        if score > best:
            best = score
            initial = result.x.copy()
            (HERE / f"{args.label}_best.json").write_text(json.dumps({"schema_version": 1, "angles": expanded.reshape(24, 2).tolist()}, indent=2) + "\n")
        (HERE / f"{args.label}_log.json").write_text(json.dumps(records, indent=2) + "\n")
        if score > (0.975 if args.robust else 0.99999999):
            break


if __name__ == "__main__":
    main()
