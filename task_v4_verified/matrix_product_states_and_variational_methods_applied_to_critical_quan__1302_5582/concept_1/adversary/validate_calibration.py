import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from hidden.suite import cases
from trusted_contractor import load_mps, measure
from evaluate import aggregate, quality


def validate():
    calibration_path = ROOT / "evaluator/hidden/calibration.json"
    calibration = json.loads(calibration_path.read_text())
    scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())
    expected = {request["case_id"]: (family, request) for family, request in cases()}
    if set(calibration["cases"]) != set(expected):
        raise ValueError("calibration does not contain every frozen case")
    if calibration["target_frozen_before_launch"] != scoring["target"]:
        raise ValueError("numeric target changed during calibration")
    for relative, digest in calibration["frozen_hashes"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen hash mismatch: " + relative)
    rows = []
    checked_states = 0
    gaps = {}
    for identity, record in calibration["cases"].items():
        family, request = expected[identity]
        if record["request"] != request or record["family"] != family:
            raise ValueError("request mismatch: " + identity)
        row = {"case_id": identity, "family": family, "stages": {}}
        for name, state in [("reference", record["reference"]), *record["baseline"].items()]:
            path = ROOT / state["state"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != state["sha256"]:
                raise ValueError("retained state hash mismatch")
            measured = measure(load_mps(path, request), request)
            if abs(measured["energy"] - state["energy"]) > 1e-9:
                raise ValueError("independent energy mismatch")
            checked_states += 1
            if name != "reference":
                budget = scoring["stages"][name]
                if not 0 <= state["cpu_seconds"] <= budget["cpu_seconds"]:
                    raise ValueError("baseline CPU budget violation")
                if not 0 <= state["wall_seconds"] <= budget["wall_seconds"]:
                    raise ValueError("baseline wall budget violation")
                row["stages"][name] = {
                    "quality": quality(measured["energy"], state["energy"],
                                       record["reference"]["energy"], request["n_sites"]),
                    "valid": True, "cpu_seconds": state["cpu_seconds"]}
        gap = min(state["energy"] for state in record["baseline"].values()) - record["reference"]["energy"]
        if gap <= 1e-7 * request["n_sites"]:
            raise ValueError("insufficient variational improvement")
        gaps[identity] = gap
        rows.append(row)
    result = {"valid": True, "case_count": len(expected), "states_checked": checked_states,
              "baseline_summary": aggregate(rows, scoring), "minimum_baseline_reference_gaps": gaps,
              "calibration_sha256": hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
              "solvability_demonstrated": False,
              "reason": "independently measured variational states; references are not a resource-feasible submitted solver"}
    destination = ROOT / "adversary/calibration_validation.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    validate()
