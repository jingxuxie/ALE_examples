"""Finite differences for private optimizer derivatives, not evaluator changes."""

import json
import time
from pathlib import Path

from finite_search import FiniteModel

import numpy as np

PACKET = Path(__file__).resolve().parents[1]


def main():
    started = time.monotonic()
    model = FiniteModel(PACKET.parents[1] / "champions/generation_3/submission.json", 0.0009, 0.0201)
    coordinates = model.base.initial.copy()
    base = model.evaluate(coordinates)
    random = np.random.default_rng(77031)
    records = []
    for trial in range(4):
        direction = random.normal(size=120)
        direction /= np.linalg.norm(direction)
        step = 2e-6
        plus, minus = model.evaluate(coordinates + step * direction), model.evaluate(coordinates - step * direction)
        finite = (plus[0] - minus[0]) / (2 * step)
        analytic = base[1] @ direction
        constraint_difference = (plus[2] - minus[2]) / (2 * step)
        constraint_analytic = base[3] @ direction
        records.append({"objective_finite_difference": float(finite), "objective_analytic": float(analytic),
                        "objective_absolute_error": float(abs(finite - analytic)),
                        "constraint_max_absolute_error": float(np.max(abs(constraint_difference - constraint_analytic)))})
    passed = all(record["objective_absolute_error"] < 0.005 and record["constraint_max_absolute_error"] < 0.0001
                 for record in records)
    report = {"passed": passed, "records": records, "runtime_seconds": time.monotonic() - started,
              "scope": "private optimization surrogate only; frozen oracle and evaluator are unchanged",
              "dad_optimizer_smoothing_floor": 1e-8,
              "initial_audit_note": "The initial central-difference audit hit the nondifferentiable zero-DAD norm. Its initial report is retained separately; private optimization now uses an explicitly smoothed norm. All artifacts are still scored with the exact unchanged DAD."}
    (PACKET / "authoring" / "private_derivative_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
