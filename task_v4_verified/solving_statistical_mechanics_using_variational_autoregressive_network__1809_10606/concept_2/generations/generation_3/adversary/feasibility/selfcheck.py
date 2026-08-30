import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import datetime
import json
import math
from pathlib import Path
import sys

import numpy as np

import kernel
import portfolio

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def pack(document):
    lower = np.asarray(document["weights"])[kernel.LOWER]
    return np.r_[np.maximum(lower, 0), np.maximum(-lower, 0), document["beta"]]


def main():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    generator = np.random.default_rng(202608282128)
    source_paths = [HERE / "baseline/witness.json"]
    source_paths.extend(sorted((HERE / "trials").glob("*/witness.json"))[:3])
    if not source_paths[0].exists():
        source_paths[0] = kernel.ROOT / "participant/baseline/witness.json"
    documents = [json.loads(path.read_text()) for path in source_paths]
    random_document = dict(documents[0])
    weights = np.tril(generator.normal(0, 0.15, (16, 16)), -1)
    random_document.update(weights=weights.tolist(), beta=1.7, order=generator.permutation(16).tolist())
    documents.append(random_document)
    metric_error = 0.0
    objective_gradient_error = 0.0
    constraint_gradient_error = 0.0
    sector_error = 0.0
    gradient_coordinates = 0
    sector_comparisons = 0
    cases = []
    for case, document in enumerate(documents):
        exact = kernel.PHYSICS.evaluate_document(document, kernel.SPEC)
        parameters = pack(document)
        plain_problem = kernel.Problem(document, 0)
        plain = plain_problem.calculate(parameters)
        errors = {name: abs(value - exact["metrics"][name]) for name, value in plain[4]["metrics"].items()}
        metric_error = max(metric_error, max(errors.values()))
        cases.append({"case": case, "max_metric_error": max(errors.values()), "valid": exact["valid"]})
        ordered = kernel.HALF[:, document["order"]]
        logits = ordered @ np.asarray(document["weights"]).T
        half_probability = 2 * np.exp(-np.logaddexp(0, -ordered * logits).sum(axis=1))
        arrays = portfolio.sector_arrays(half_probability)
        for identifier in generator.integers(0, 65536, 12):
            distances = np.count_nonzero(kernel.HALF != kernel.SPINS[identifier], axis=1)
            for radius in (2, 3, 4):
                direct = float(half_probability @ (np.minimum(distances, 16 - distances) <= radius))
                sector_error = max(sector_error, abs(direct - arrays[radius][identifier]))
                sector_comparisons += 1
        for penalty in (0, 100):
            problem = kernel.Problem(document, penalty)
            analytic = problem.calculate(parameters)
            coordinates = np.r_[generator.choice(240, size=10, replace=False), 240]
            for coordinate in coordinates:
                step = 2e-5
                shift = np.zeros(241)
                shift[coordinate] = step
                plus = problem.calculate(parameters + shift)
                minus = problem.calculate(parameters - shift)
                numerical_objective = (plus[0] - minus[0]) / (2 * step)
                numerical_constraints = (plus[2] - minus[2]) / (2 * step)
                objective_gradient_error = max(objective_gradient_error, abs(numerical_objective - analytic[1][coordinate]))
                constraint_gradient_error = max(constraint_gradient_error, float(np.max(np.abs(numerical_constraints - analytic[3][:, coordinate]))))
                gradient_coordinates += 1
    evidence = {"checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "seed": 202608282128, "cases": cases, "gradient_coordinates": gradient_coordinates,
                "sector_comparisons": sector_comparisons, "maximum_metric_error": metric_error,
                "maximum_objective_gradient_error": objective_gradient_error,
                "maximum_constraint_gradient_error": constraint_gradient_error,
                "maximum_xor_sector_error": sector_error,
                "method": "half-enumeration versus frozen full evaluator; central finite differences including gradient-penalty Hessian action; XOR convolution versus direct masks"}
    evidence["passed"] = bool(metric_error < 1e-9 and objective_gradient_error < 3e-5 and constraint_gradient_error < 1e-7 and sector_error < 1e-12)
    (HERE / "selfcheck.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps(evidence, indent=2))
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
