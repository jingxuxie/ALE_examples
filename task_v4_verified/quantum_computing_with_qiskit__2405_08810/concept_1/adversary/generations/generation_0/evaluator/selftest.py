import copy
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def main():
    specification = importlib.util.spec_from_file_location("baseline", ROOT / "participant" / "baseline" / "solution.py")
    baseline = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(baseline)
    checks = 0
    for size in range(2, 9):
        operations = baseline.remote_sequence(list(range(size)))
        for bitstring in range(1 << size):
            actual = bitstring
            for kind, control, target in operations:
                actual ^= ((actual >> control) & 1) << target
            expected = bitstring ^ ((bitstring & 1) << (size - 1))
            assert actual == expected
            checks += 1
    randomizer = random.Random(70021)
    for unused in range(15):
        size = randomizer.randrange(3, 8)
        edges = [[control, target, 1, 1] for control in range(size) for target in range(size) if abs(control - target) == 1]
        masks = randomizer.sample(range(1, 1 << size), min(9, (1 << size) - 1))
        instance = {"n": size, "edges": edges, "terms": masks}
        response = baseline.compile_circuit(instance)
        check(instance, response)
        for bitstring in range(1 << size):
            actual = bitstring
            phases = {}
            for kind, first, second in response["ops"]:
                if kind == "cx":
                    actual ^= ((actual >> first) & 1) << second
                else:
                    phases[second] = (actual >> first) & 1
            assert actual == bitstring
            assert phases == {index: (mask & bitstring).bit_count() % 2 for index, mask in enumerate(masks)}
            checks += 1
        invalid = copy.deepcopy(response)
        invalid["ops"].append(["cx", 0, 1])
        try:
            check(instance, invalid)
            raise AssertionError("corrupted final map accepted")
        except ValueError:
            checks += 1
    for case in json.loads((ROOT / "evaluator" / "hidden" / "cases.json").read_text()):
        assert check(case["input"], baseline.compile_circuit(case["input"])) == case["baseline"]
        checks += 1
    instance = {"n": 2, "edges": [[0, 1, 3, 2], [1, 0, 4, 1]], "terms": [3]}
    valid = {"ops": [["cx", 0, 1], ["rz", 1, 0], ["cx", 0, 1]]}
    assert check(instance, valid) == {"cost": 6.8, "error_weight": 6, "makespan": 4, "cx_count": 2}
    mutations = [
        {"ops": []},
        {"ops": [["cx", True, 1], ["rz", 1, 0], ["cx", 0, 1]]},
        {"ops": [["cx", 0, 0]]},
        {"ops": [["cx", 0, 2]]},
        {"ops": [["rz", 1, 0]]},
        {"ops": valid["ops"] + [["rz", 0, 0]]},
        {"ops": valid["ops"], "free_permutation": [1, 0]},
    ]
    for mutation in mutations:
        try:
            check(instance, mutation)
            raise AssertionError("malformed or incorrect circuit accepted")
        except ValueError:
            checks += 1
    from evaluate import strict_json
    for invalid_json in ('{"ops":[],"ops":[]}', '{"ops":NaN}', '{"ops":Infinity}'):
        try:
            strict_json(invalid_json)
            raise AssertionError("ambiguous or nonfinite JSON accepted")
        except ValueError:
            checks += 1
    report = {"passed": True, "checks": checks, "independent_semantics": "exhaustive computational-basis symbolic phase tracking on small systems", "mutation_rejection": True}
    (ROOT / "adversary" / "selftest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
