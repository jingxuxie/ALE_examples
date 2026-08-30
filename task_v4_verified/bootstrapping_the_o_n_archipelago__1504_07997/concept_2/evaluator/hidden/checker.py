import argparse
import json
import math
from pathlib import Path

import numpy as np


def check_case(instance, answer):
    atoms = answer.get("atoms")
    if not isinstance(atoms, list) or not 1 <= len(atoms) <= instance["max_atoms"]:
        return False, math.inf, "invalid atom count"
    design = np.asarray(instance["design"], dtype=float)
    prediction = np.zeros_like(np.asarray(instance["target"], dtype=float))
    indices = set()
    shared = None
    trace = 0.0
    for atom in atoms:
        if not isinstance(atom, dict):
            return False, math.inf, "invalid atom"
        index = atom.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or index in indices:
            return False, math.inf, "duplicate or noninteger index"
        if not 0 <= index < design.shape[1]:
            return False, math.inf, "index out of range"
        indices.add(index)
        vector = np.asarray(atom.get("ope"), dtype=float)
        if vector.shape != (2,) or not np.isfinite(vector).all() or np.max(np.abs(vector)) > 4:
            return False, math.inf, "invalid OPE vector"
        first, second = vector
        trace += float(vector @ vector)
        prediction += design[:, index, None] * np.array([first**2, first*second, second**2])
        if index == 0:
            shared = first**2
    if shared is None or abs(shared - instance["shared_ope_squared"]) > 2e-10:
        return False, math.inf, "shared OPE condition"
    if trace > instance["trace_budget"] + 2e-10:
        return False, math.inf, "trace budget"
    residual = float(np.max(np.abs(prediction - instance["target"]) / instance["scales"]))
    return residual <= 2e-8, residual, "valid" if residual <= 2e-8 else "moment residual"


def score(instances, answer):
    expected = {instance["id"] for instance in instances}
    if not isinstance(answer, dict) or not isinstance(answer.get("cases"), list):
        raise ValueError("answer must contain a cases list")
    submitted = {}
    for case in answer["cases"]:
        if not isinstance(case, dict) or case.get("id") not in expected or case["id"] in submitted:
            raise ValueError("unknown, repeated, or invalid case id")
        submitted[case["id"]] = case
    details = []
    families = {}
    for instance in instances:
        valid, residual, reason = check_case(instance, submitted.get(instance["id"], {}))
        details.append({"id": instance["id"], "valid": bool(valid),
                        "residual": residual if math.isfinite(residual) else None, "reason": reason})
        families.setdefault(instance["family"], []).append(int(valid))
    core = sum(detail["valid"] for detail in details) / len(details)
    family_scores = {family: sum(values) / len(values) for family, values in families.items()}
    return {"core_score": core, "worst_family_score": min(family_scores.values()),
            "family_scores": family_scores, "valid": core == 1.0, "passed": core == 1.0,
            "runtime_score": 1.0, "reason": "all certificates valid" if core == 1 else "incomplete valid certificate set",
            "cases": details}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("instances")
    parser.add_argument("answer")
    arguments = parser.parse_args()
    try:
        instances = json.loads(Path(arguments.instances).read_text())["instances"]
        answer = json.loads(Path(arguments.answer).read_text())
        result = score(instances, answer)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
                  "valid": False, "passed": False, "reason": str(error)}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
