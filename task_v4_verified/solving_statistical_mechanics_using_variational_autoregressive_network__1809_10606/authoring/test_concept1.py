import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evaluator1", ROOT / "concept_1" / "evaluator" / "evaluate.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.path.insert(0, str(ROOT / "concept_1" / "participant" / "workspace"))
from van import exact_metrics


def main():
    rng = np.random.default_rng(438)
    tests = []
    for count in (2, 5, 9):
        couplings = np.tril(rng.normal(0, 0.4, (count, count)), -1)
        couplings += couplings.T
        instance = {"n": count, "couplings": couplings.tolist(), "fields": rng.normal(0, 0.2, count).tolist()}
        weights = [np.tril(rng.normal(0, 0.5, (count, count)), -1).tolist() for component in range(3)]
        model = {"weights": weights, "biases": rng.normal(0, 0.2, (3, count)).tolist(),
                 "orders": [list(range(count))] * 3, "mixing": [0.2, 0.3, 0.5]}
        first, second = MODULE.exact_score(instance, model), exact_metrics(instance, model)
        assert abs(first["kl"] - second["kl"]) < 1e-12
        assert abs(first["ess"] - second["ess"]) < 1e-12
        tests.append({"n": count, "independent_energies_and_log_probability": "passed", "normalization": first["log_norm"]})
    count = 8
    couplings = np.zeros((count, count))
    for site in range(1, count):
        couplings[site, site - 1] = couplings[site - 1, site] = 0.3 + 0.07 * site
    weights = 2 * np.tril(couplings, -1)
    instance = {"n": count, "couplings": couplings.tolist(), "fields": [0.] * count}
    model = {"weights": [weights.tolist()], "biases": [[0.] * count], "orders": [list(range(count))], "mixing": [1.]}
    metrics = MODULE.exact_score(instance, model)
    assert metrics["kl"] < 1e-12 and abs(metrics["ess"] - 1) < 1e-12
    tests.append({"exact_chain": "passed", "metrics": metrics})
    for corruption in ("noncausal", "normalization", "nonfinite", "order"):
        value = json.loads(json.dumps(model))
        if corruption == "noncausal":
            value["weights"][0][0][1] = 0.1
        elif corruption == "normalization":
            value["mixing"] = [2.]
        elif corruption == "nonfinite":
            value["biases"][0][0] = float("nan")
        else:
            value["orders"][0][0] = 1
        try:
            MODULE.validate_model(value, count)
        except ValueError:
            tests.append({"reject_" + corruption: "passed"})
        else:
            raise AssertionError("invalid artifact accepted")
    result = {"valid": True, "tests": tests, "exact_enumeration": True, "reference_implementation_required": False}
    (ROOT / "concept_1" / "adversary" / "evaluator_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
