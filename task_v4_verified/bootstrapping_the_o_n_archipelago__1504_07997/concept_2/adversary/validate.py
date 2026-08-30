import copy
import importlib.util
import json
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]


def main():
    specification = importlib.util.spec_from_file_location("checker", ROOT / "evaluator/hidden/checker.py")
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    instances = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
    state = json.loads((ROOT / "status.json").read_text())
    witness_path = ROOT / state.get("private_witness", "adversary/planted.json")
    witness = json.loads(witness_path.read_text())
    report = {"planted": checker.score(instances, witness), "mutations": {}}
    for label, edit in (
        ("nan", lambda answer: answer["cases"][0]["atoms"][0]["ope"].__setitem__(0, float("nan"))),
        ("infinite", lambda answer: answer["cases"][0]["atoms"][0]["ope"].__setitem__(0, float("inf"))),
        ("zero", lambda answer: answer["cases"][0].__setitem__("atoms", [])),
        ("duplicate_atom", lambda answer: answer["cases"][0]["atoms"].append(answer["cases"][0]["atoms"][0])),
        ("changed_coefficient", lambda answer: answer["cases"][0]["atoms"][1]["ope"].__setitem__(0, 0.123)),
        ("missing_case", lambda answer: answer["cases"].pop()),
    ):
        changed = copy.deepcopy(witness)
        edit(changed)
        result = checker.score(instances, changed)
        assert not result["passed"], label
        report["mutations"][label] = "rejected"
    mp.mp.dps = 70
    maximum = mp.mpf(0)
    for instance, case in zip(instances, witness["cases"]):
        for row_index, row in enumerate(instance["design"]):
            for component in range(3):
                total = mp.mpf(0)
                for atom in case["atoms"]:
                    first, second = map(lambda value: mp.mpf(str(value)), atom["ope"])
                    product = (first*first, first*second, second*second)[component]
                    total += mp.mpf(str(row[atom["index"]]))*product
                residual = abs(total - mp.mpf(str(instance["target"][row_index][component])))
                residual /= mp.mpf(str(instance["scales"][row_index][component]))
                maximum = max(maximum, residual)
    assert maximum < mp.mpf("1e-12")
    report["independent_70_digit_max_scaled_residual"] = str(maximum)
    report["generation"] = state["generation"]
    report["witness_source"] = str(witness_path.relative_to(ROOT))
    (ROOT / "adversary/validation_current.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"valid": True, "mutations_rejected": len(report["mutations"]),
                      "independent_residual": str(maximum)}, indent=2))


if __name__ == "__main__":
    main()
