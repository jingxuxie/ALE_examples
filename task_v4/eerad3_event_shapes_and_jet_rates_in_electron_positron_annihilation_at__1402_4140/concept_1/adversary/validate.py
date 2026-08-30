import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

CONCEPT = Path(__file__).resolve().parents[1]
ROOT = CONCEPT.parent
sys.path.insert(0, str(ROOT / "research"))
from build_prediction import native_values


def main():
    spec = importlib.util.spec_from_file_location("prediction_evaluator", CONCEPT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    data = np.load(CONCEPT / "evaluator/hidden/test.npz")
    exact = evaluator.score(data["log_weight"], data["log_weight"], data["family"])
    assert exact["passed"]
    biased = evaluator.score(data["log_weight"] + 0.15, data["log_weight"], data["family"])
    assert not biased["passed"]
    permutation = np.arange(len(data["s"]))[::-1]
    shuffled = evaluator.score(data["log_weight"][permutation], data["log_weight"], data["family"])
    assert not shuffled["passed"]
    malformed = []
    for invalid in (np.zeros((len(data["s"]), 1)), np.full(len(data["s"]), np.nan),
                    np.full(len(data["s"]), 1e308)):
        try:
            evaluator.score(invalid, data["log_weight"], data["family"])
            malformed.append(False)
        except ValueError:
            malformed.append(True)
    assert all(malformed)
    reverse = [0, 3, 2, 1, 6, 5, 4, 9, 8, 7]
    samples = data["s"][:200]
    first = native_values(samples, CONCEPT / "adversary/native")
    second = native_values(samples[:, reverse], CONCEPT / "adversary/native")
    reversal_error = float(np.max(np.abs(first - second) / first))
    assert reversal_error < 1e-12
    labels = data["log_weight"]
    family_stress = []
    for family_index in range(5):
        altered = labels.copy()
        altered[data["family"] == family_index] += 0.12
        result = evaluator.score(altered, labels, data["family"])
        family_stress.append(not result["passed"])
    assert all(family_stress)
    result = {"exact_predictions_pass": True, "biased_predictions_rejected": True,
              "shuffled_predictions_rejected": True, "malformed_predictions_rejected": malformed,
              "every_single_family_failure_rejected": family_stress,
              "native_reversal_max_relative_error": reversal_error,
              "source_generator": "quadruple-precision official leading-colour pair, positive physical inputs"}
    (CONCEPT / "adversary/checker_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
