import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "participant/baseline"))
from contract import canonical, validate
from solve import solve


def numerical(case, plan):
    generator = np.random.default_rng(592145)
    dimensions = {"o": 2, "v": 3}
    tensors = {name: generator.normal(size=tuple(dimensions[space] for space in shape))
               for name, shape in case["tensors"].items()}
    originals = dict(tensors)
    errors = []
    for step in plan["steps"]:
        if "delete" in step:
            del tensors[step["delete"]]
        elif "emit" in step:
            name, labels = step["input"]
            actual = np.einsum(labels + "->" + step["output"], tensors[name])
            term = case["terms"][step["emit"]]
            expression = ",".join(reference[1] for reference in term["inputs"]) + "->" + term["output"]
            expected = np.einsum(expression, *(originals[name] for name, labels in term["inputs"]), optimize=False)
            error = np.max(np.abs(actual - expected)) / max(1, np.max(np.abs(expected)))
            errors.append(float(error))
        else:
            expression = ",".join(reference[1] for reference in step["inputs"]) + "->" + step["output"]
            tensors[step["id"]] = np.einsum(expression, *(tensors[name] for name, labels in step["inputs"]))
    return max(errors)


def main():
    records = []
    for path in sorted((ROOT / "participant/input").glob("*.json")):
        if ".baseline." in path.name:
            continue
        case = json.loads(path.read_text())
        plan = solve(case)
        metric = validate(case, plan)
        error = numerical(case, plan)
        assert error < 2e-11, error
        mutations = []
        omitted = copy.deepcopy(plan)
        omitted["steps"] = [step for step in omitted["steps"] if step.get("emit") != 0]
        mutations.append(omitted)
        duplicate = copy.deepcopy(plan)
        duplicate["steps"] += [next(step for step in duplicate["steps"] if "emit" in step)]
        mutations.append(duplicate)
        corrupt = copy.deepcopy(plan)
        first = next(step for step in corrupt["steps"] if "id" in step)
        first["output"] += "Z"
        mutations.append(corrupt)
        rejected = 0
        for mutation in mutations:
            try:
                validate(case, mutation)
            except (ValueError, TypeError, KeyError):
                rejected += 1
        assert rejected == len(mutations)
        cap_case = copy.deepcopy(case)
        cap_case["memory_cap"] = metric["peak_elements"] - 1
        try:
            validate(cap_case, plan)
            raise AssertionError("memory cap was ignored")
        except ValueError:
            pass
        records.append({"family": path.stem, "numerical_relative_error": error,
                        "negative_controls_rejected": rejected + 1})
    result = {"valid": True, "independent_numeric_oracle": "unoptimized NumPy einsum on complete source monomials",
              "results": records}
    (ROOT / "adversary/audit.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
