import argparse
import json
import math
from pathlib import Path
import stat
import time

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]


def read_witness(path, model):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("A certificate must be a regular JSON artifact, not a symlink")
    if path.is_dir():
        path = path / "witness.json"
    information = path.lstat()
    if not stat.S_ISREG(information.st_mode):
        raise ValueError("A certificate must be a regular JSON artifact")
    if information.st_size > model["max_artifact_bytes"]:
        raise ValueError("Artifact exceeds the public size limit")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or set(payload) != {"fields"}:
        raise ValueError("Expected exactly the fields key")
    fields = payload["fields"]
    if not isinstance(fields, list) or len(fields) != model["time_slices"]:
        raise ValueError("Incorrect number of time slices")
    for row in fields:
        if not isinstance(row, list) or len(row) != model["linear_size"] ** 2:
            raise ValueError("Incorrect number of sites")
        if any(type(value) is not int or value not in (-1, 1) for value in row):
            raise ValueError("Fields must be integer -1 or +1")
    return fields


def precision_weight(fields, model, point, precision):
    with mp.workdps(precision):
        size = model["linear_size"]
        sites = size ** 2
        beta = mp.mpf(str(model["beta"])) * mp.mpf(str(point["beta_multiplier"]))
        chemical = mp.mpf(str(model["chemical_potential"])) + mp.mpf(str(point["chemical_shift"]))
        delta = beta / model["time_slices"]
        coupling = mp.acosh(mp.exp(delta * mp.mpf(str(model["interaction"])) / 2))
        kinetic = mp.matrix(sites)
        for source in range(sites):
            source_horizontal, source_vertical = divmod(source, size)
            for target in range(sites):
                target_horizontal, target_vertical = divmod(target, size)
                displacement_horizontal = (target_horizontal - source_horizontal) % size
                displacement_vertical = (target_vertical - source_vertical) % size
                nearest = (displacement_horizontal in (1, size - 1) and displacement_vertical == 0) or (displacement_vertical in (1, size - 1) and displacement_horizontal == 0)
                kinetic[source, target] = -mp.mpf(str(model["hopping"])) if nearest else mp.mpf(0)
        half_step = mp.expm(-delta * kinetic / 2)
        signs = []
        logarithms = []
        for spin in (1, -1):
            product = mp.eye(sites)
            for row in fields:
                diagonal = mp.diag([mp.exp(spin * coupling * entry + delta * chemical) for entry in row])
                product = half_step * diagonal * half_step * product
            determinant = mp.det(mp.eye(sites) + product)
            signs.append(int(mp.sign(determinant)))
            logarithms.append(mp.log(abs(determinant)) if determinant else mp.ninf)
        return signs, mp.fsum(logarithms)


def evaluate(path, model=None):
    started = time.monotonic()
    model = json.loads((ROOT / "participant" / "input" / "model.json").read_text()) if model is None else model
    result = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
              "resource_score": 0.0, "passed": False, "valid": False, "reason": "", "points": []}
    result["physical_model"] = {key: model[key] for key in ("linear_size", "time_slices", "interaction", "chemical_potential", "beta", "hopping")}
    try:
        fields = read_witness(path, model)
        result["valid"] = True
        for point in model["certification_points"]:
            lower_signs, lower_log = precision_weight(fields, model, point, model["precision_digits"][0])
            upper_signs, upper_log = precision_weight(fields, model, point, model["precision_digits"][1])
            with mp.workdps(model["precision_digits"][1]):
                discrepancy = abs(lower_log - upper_log)
                agreed = bool(mp.isfinite(discrepancy) and discrepancy < mp.mpf(str(model["log_weight_agreement_tolerance"])))
            negative = math.prod(lower_signs) == -1 and math.prod(upper_signs) == -1
            result["points"].append({"parameters": point, "lower_spin_signs": lower_signs,
                                     "upper_spin_signs": upper_signs, "logabs_weight": str(upper_log),
                                     "log_discrepancy": str(discrepancy), "precision_agreement": agreed,
                                     "negative": negative, "passed": bool(negative and agreed)})
        point_scores = [int(point["passed"]) for point in result["points"]]
        result["core_score"] = sum(point_scores) / len(point_scores)
        result["worst_family_score"] = float(min(point_scores))
        result["passed"] = all(point_scores)
        result["reason"] = "All certification points have independently reproduced negative weights" if result["passed"] else "At least one certification point lacks a precision-stable negative weight"
    except (ValueError, TypeError, OSError, OverflowError, ZeroDivisionError, RecursionError) as error:
        result["reason"] = f"Rejected: {error}"
    elapsed = time.monotonic() - started
    result["runtime_seconds"] = elapsed
    result["runtime_score"] = 1.0 / (1.0 + elapsed / 180)
    result["resource_score"] = result["runtime_score"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    report = evaluate(arguments.submission)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(encoded)
    print(encoded, end="")
