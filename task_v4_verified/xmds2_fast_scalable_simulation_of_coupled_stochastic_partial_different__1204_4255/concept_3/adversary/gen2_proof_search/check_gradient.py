import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import optimizer_copy as opt


def main():
    os.chdir(HERE)
    cases = opt.fc.read_json(ROOT / "evaluator/hidden/cases.json")
    selected = [cases[index] for index in (0, 21, 30)]
    vector = opt.load(ROOT / "champions/generation_1/control.json")
    objective = opt.Objective(selected, (48, 24), 0.04, 60.0, 100000.0)
    value, gradient = objective(vector)
    initial_scores = objective.scores.copy()
    checks = []
    for index in (2, 21, 40, 63, 80, 98):
        plus, minus = vector.copy(), vector.copy()
        plus[index] += 1e-5
        minus[index] -= 1e-5
        numeric = (objective(plus)[0] - objective(minus)[0]) / 2e-5
        checks.append({"index": index, "adjoint": float(gradient[index]), "numeric": float(numeric), "absolute_difference": float(abs(gradient[index] - numeric))})
    splines, diagnostics = opt.fc.validate_artifact(opt.artifact(vector), opt.PROTOCOL)
    state, numerical = opt.fc.evolve(splines, selected, (48, 24), 0.04, objective.initial)
    scores = opt.fc.fidelities(state, objective.target, (48, 24))
    difference = float(np.max(np.abs(scores - initial_scores)))
    result = {"gradient_checks": checks, "max_independent_forward_fidelity_difference": difference, "passed": max(check["absolute_difference"] for check in checks) < 2e-5 and difference < 1e-11}
    (HERE / "gradient_check.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    assert result["passed"]


if __name__ == "__main__":
    main()
