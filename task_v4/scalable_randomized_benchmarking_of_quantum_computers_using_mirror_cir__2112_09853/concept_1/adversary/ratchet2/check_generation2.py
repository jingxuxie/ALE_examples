import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


def check(payload):
    original = verify.verify(payload)
    gates = verify.make_gates(payload)
    baseline_gates = verify.make_gates(verify.uniform_payload())
    families = []
    for name, selection, target_overlap in (("single", range(24), 28800), ("cx", range(24, 32), 1920)):
        defects = []
        for pauli in verify.PAULIS[1:]:
            actual = sum(gates[index]["counts"].get(pauli, 0) for index in selection)
            expected = sum(baseline_gates[index]["counts"].get(pauli, 0) for index in selection)
            if actual != expected:
                defects.append({"pauli": "".join("IXZY"[digit] for digit in pauli),
                                "actual": actual, "expected": expected, "difference": actual - expected})
        overlap = sum(sum(count * gates[index]["counts"].get(verify.transform(gates[index]["key"], pauli), 0)
                          for pauli, count in gates[gates[index]["inverse"]]["counts"].items())
                      for index in selection)
        families.append({"family": name, "mean_channel_pass": not defects,
                         "max_mean_count_defect": max((abs(row["difference"]) for row in defects), default=0),
                         "mean_channel_defects": defects, "overlap": overlap, "overlap_target": target_overlap,
                         "pair_calibration_pass": overlap == target_overlap})
    stratified = all(family["mean_channel_pass"] and family["pair_calibration_pass"] for family in families)
    return {"generation": 2, "contract_status": "hard_open", "original_contract_pass": original["accepted"],
            "admissible": stratified, "passed": original["accepted"] and stratified,
            "nominal_fit": original["fit"], "S256": original["polarizations"][-1], "family_calibrations": families}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    arguments = parser.parse_args()
    try:
        result = check(json.loads(Path(arguments.witness).read_text()))
    except (ValueError, TypeError, OSError) as error:
        result = {"generation": 2, "admissible": False, "passed": False, "reason": str(error)}
    print(json.dumps(result, indent=2, allow_nan=False))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
