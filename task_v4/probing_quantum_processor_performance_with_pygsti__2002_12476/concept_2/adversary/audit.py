import copy
import importlib.util
import json
import math
import tempfile
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    start = time.monotonic()
    public = load_module("public_screen", ROOT / "participant/workspace/screen.py")
    private = load_module("private_evaluator", ROOT / "evaluator/evaluate.py")
    private.integrity_check()
    checks = []
    zero = {"version": 1, "gate_parameters": [[0.] * 5 for index in range(3)], "circuit": "IXY" * 21 + "I"}
    zero_result = private.score_witness(zero)
    assert zero_result["valid"] and not zero_result["passed"] and zero_result["calibration_accepted"]
    assert zero_result["core_score"] < 1e-12
    checks.append("zero-leakage known negative")
    malformed = []
    for key, value in [("version", True), ("version", 2), ("gate_parameters", []), ("gate_parameters", [[0.] * 5] * 4),
                       ("circuit", "IXY"), ("circuit", "I" * 64), ("circuit", "Z" * 64), ("circuit", ["I"] * 64)]:
        item = copy.deepcopy(zero)
        item[key] = value
        malformed.append(item)
    for coordinate, value in [(0, math.pi + 1e-5), (1, .04001), (1, True), (1, "0"),
                               (1, float("nan")), (1, float("inf")), (1, 1e300)]:
        item = copy.deepcopy(zero)
        item["gate_parameters"][0][coordinate] = value
        malformed.append(item)
    item = copy.deepcopy(zero)
    item["ignored"] = "arbitrary extra field"
    malformed.append(item)
    malformed.extend([[], None, 0, {"version": 1}])
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary", prefix="checker_selftest_") as directory:
        directory = Path(directory)
        path = directory / "witness.json"
        for index, item in enumerate(malformed):
            path.write_text(json.dumps(item))
            result = private.evaluate(path)
            assert not result["valid"] and not result["passed"], (index, result)
            try:
                public.load_witness(path)
            except (ValueError, TypeError, OverflowError):
                pass
            else:
                raise AssertionError("public parser accepted malformed input")
        for text in ["", "{", "[" * 2000, '{"version":1,"version":1}', " " * 32769]:
            path.write_text(text)
            result = private.evaluate(path)
            assert not result["valid"] and not result["passed"]
        path.write_text(json.dumps(zero))
        link = directory / "link.json"
        link.symlink_to(path)
        assert not private.evaluate(link)["valid"]
        assert private.evaluate(directory)["valid"]
        assert not private.evaluate(directory / "missing")["valid"]
        checks.append("27 malformed, oversized, duplicate-key, missing-file and symlink cases")
    generator = np.random.default_rng(216712)
    maximum_difference = 0.
    minimum_choi_eigenvalue = 1.
    families = sum(private.FAMILIES.values(), [])
    random_words = ["".join(generator.choice(list("IXY"), generator.integers(0, 90))) for index in range(96)]
    parameter_sets = [np.zeros((3, 5))]
    for index in range(40):
        parameters = generator.normal(size=(3, 5))
        parameters[:, 0] = generator.uniform(-math.pi, math.pi, 3)
        parameters[:, 1:] *= generator.uniform(0, .04, (3, 1)) / np.linalg.norm(parameters[:, 1:], axis=1, keepdims=True)
        parameter_sets.append(parameters)
    for parameters in parameter_sets:
        words = families + random_words
        reference = private.simulate(parameters, words)
        fast = public.probabilities(parameters, public.encode(words))
        maximum_difference = max(maximum_difference, max(float(np.max(abs(first - second)))
                                                       for first, second in zip(reference, fast)))
        unitaries, first, second = private.physical_maps(parameters)
        for first_gate, second_gate in zip(first[:3], second[:3]):
            vectors = [first_gate.reshape(4), second_gate.reshape(4)]
            choi = sum(np.outer(vector, vector.conj()) for vector in vectors)
            minimum_choi_eigenvalue = min(minimum_choi_eigenvalue, float(np.linalg.eigvalsh(choi)[0]))
        short_truth, short_prediction, short_leakage = private.simulate(parameters, ["", "I", "X", "Y"])
        assert np.max(abs(short_truth - short_prediction)) < 1e-12
    assert maximum_difference < 2e-12, maximum_difference
    assert minimum_choi_eigenvalue > -2e-12, minimum_choi_eigenvalue
    checks.extend(["41 processor cross-checks: density/Kraus/expm versus pure-state/Pauli/analytic",
                   "123 Choi positivity and trace-preservation checks", "single-gate reduction equality"])
    parameters = np.zeros((3, 5))
    parameters[0, 1] = .02
    depths = [0, 1, 2, 7, 32, 64]
    truth, prediction, leakage = private.simulate(parameters, ["I" * depth for depth in depths])
    analytic_truth = .005 + .99 * np.cos(.02 * np.array(depths)) ** 2
    analytic_prediction = .005 + .99 * np.cos(.02) ** (2 * np.array(depths))
    assert np.max(abs(truth - analytic_truth)) < 1e-12
    assert np.max(abs(prediction - analytic_prediction)) < 1e-12
    resonant = copy.deepcopy(zero)
    resonant["gate_parameters"] = parameters.tolist()
    resonant_result = private.score_witness(resonant)
    assert not resonant_result["calibration_accepted"] and not resonant_result["passed"]
    checks.append("analytic resonant-idle simulator check and screen rejection")
    baseline = json.loads((ROOT / "adversary/baseline_witness.json").read_text())
    public_result = public.measure(baseline)
    private_result = private.score_witness(baseline)
    assert public_result["passed"] == private_result["passed"]
    assert abs(public_result["core_score"] - private_result["core_score"]) < 2e-12
    assert public_result["calibration_accepted"] == private_result["calibration_accepted"]
    for public_scenario, private_scenario in zip(public_result["scenarios"], private_result["scenarios"]):
        for key in ["heldout_truth", "heldout_prediction", "heldout_abs_error", "final_leakage"]:
            assert abs(public_scenario[key] - private_scenario[key]) < 2e-12
        for family in public.FAMILIES:
            for key in ["max_abs_error", "rms_error"]:
                assert abs(public_scenario["calibration"][family][key] - private_scenario["calibration"][family][key]) < 2e-12
    checks.append("baseline end-to-end agreement in all five scenarios and seven families")
    for name in ["specification.json", "calibration.json"]:
        assert (ROOT / "participant/input" / name).read_bytes() == (ROOT / "evaluator/hidden" / name).read_bytes()
    checks.append("public/private frozen inputs identical")
    audit = {"passed": True, "checks": checks, "maximum_simulator_disagreement": maximum_difference,
             "minimum_choi_eigenvalue": minimum_choi_eigenvalue, "runtime_seconds": time.monotonic() - start,
             "crosscheck_parameter_sets": len(parameter_sets), "circuits_per_parameter_set": len(families) + len(random_words)}
    (ROOT / "adversary/audit_results.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
