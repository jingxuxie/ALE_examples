import copy
import importlib.util
import json
from pathlib import Path
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_2"
EVIDENCE = ROOT / "adversary/generation_1"


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    public = load("phase_public", ROOT / "participant/workspace/screen.py")
    private = load("phase_private", ROOT / "evaluator/evaluate.py")
    old = load("phase_original", ROOT / "generations/generation_0/evaluator/evaluate.py")
    private.integrity_check()
    assert public.SPEC == private.SPEC
    assert public.FAMILIES == private.FAMILIES == old.FAMILIES
    assert private.SPEC["scenarios"][:5] == old.SPEC["scenarios"]
    champion = private.read_submission(ROOT / "participant/baseline/witness.json")
    assert old.score_witness(champion)["passed"]
    baseline = private.score_witness(champion)
    assert baseline["valid"] and not baseline["passed"]
    (EVIDENCE / "baseline_score.json").write_text(json.dumps(baseline, indent=2) + "\n")
    generator = np.random.default_rng(668527)
    witnesses = [champion]
    for trial in range(12):
        parameters = generator.normal(size=(3, 5))
        parameters[:, 0] = generator.uniform(-np.pi, np.pi, 3)
        parameters[:, 1:] *= generator.uniform(0, .04, (3, 1)) / np.linalg.norm(parameters[:, 1:], axis=1, keepdims=True)
        witnesses.append(dict(version=1, gate_parameters=parameters.tolist(), circuit=champion["circuit"]))
    maximum_difference = 0.
    for witness in witnesses:
        fast = public.measure(witness)
        dense = private.score_witness(witness)
        assert fast["passed"] == dense["passed"]
        for first, second in zip(fast["scenarios"], dense["scenarios"]):
            for field in ("heldout_truth", "heldout_prediction", "heldout_abs_error", "final_leakage"):
                maximum_difference = max(maximum_difference, abs(first[field] - second[field]))
            for family in private.FAMILIES:
                for field in ("max_abs_error", "rms_error"):
                    maximum_difference = max(maximum_difference,
                        abs(first["calibration"][family][field] - second["calibration"][family][field]))
    assert maximum_difference < 2e-12
    malformed = []
    for key, value in [("version", True), ("version", 2), ("gate_parameters", []),
                       ("circuit", "I" * 64), ("circuit", "X" * 63), ("extra", 1)]:
        item = copy.deepcopy(champion)
        item[key] = value
        malformed.append(json.dumps(item))
    for coordinate, value in [(0, 3.2), (1, .05), (1, True), (1, "0"), (1, float("nan"))]:
        item = copy.deepcopy(champion)
        item["gate_parameters"][0][coordinate] = value
        malformed.append(json.dumps(item))
    malformed.extend(['{"version":1,"version":1}', '{}', 'null', '[]', '{', ' ' * 32769])
    with tempfile.TemporaryDirectory() as directory:
        artifact = Path(directory) / "witness.json"
        for payload in malformed:
            artifact.write_text(payload)
            result = private.evaluate(artifact)
            assert not result["valid"] and not result["passed"]
        artifact.write_text(json.dumps(champion))
        alias = Path(directory) / "alias.json"
        alias.symlink_to(artifact)
        assert not private.evaluate(alias)["valid"]
        assert private.evaluate(artifact)["valid"]
    result = dict(passed=True, original_champion_passed=True, new_champion_failed=True,
                  original_five_scenarios_retained=True, thresholds_and_calibration_unchanged=True,
                  simulator_code_unchanged=True, randomized_witnesses=len(witnesses),
                  independently_compared_scenarios=len(witnesses) * 21,
                  maximum_probability_difference=maximum_difference, malformed_cases=len(malformed) + 1)
    for relative in ("participant/workspace/screen.py", "evaluator/evaluate.py"):
        assert (ROOT / relative).read_bytes() == (ROOT / "generations/generation_0" / relative).read_bytes()
    (EVIDENCE / "evaluator_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
