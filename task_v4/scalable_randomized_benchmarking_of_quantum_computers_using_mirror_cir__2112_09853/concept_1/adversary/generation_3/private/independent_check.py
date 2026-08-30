import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import verify


def check(payload):
    original = verify.verify(payload)
    gates = verify.make_gates(payload)
    controls = verify.make_gates(verify.uniform_payload())
    families = []
    for name, selection, target in (("single", range(24), 28800), ("cx", range(24, 32), 1920)):
        differences = []
        for pauli in verify.PAULIS[1:]:
            actual = sum(gates[index]["counts"].get(pauli, 0) for index in selection)
            expected = sum(controls[index]["counts"].get(pauli, 0) for index in selection)
            if actual != expected:
                differences.append({"pauli": "".join("IXZY"[digit] for digit in pauli),
                                    "actual": actual, "expected": expected, "difference": actual - expected})
        overlap = sum(sum(count * gates[index]["counts"].get(verify.transform(gates[index]["key"], pauli), 0)
                          for pauli, count in gates[gates[index]["inverse"]]["counts"].items())
                      for index in selection)
        families.append({"family": name, "mean_channel_pass": not differences,
                         "max_mean_count_defect": max((abs(row["difference"]) for row in differences), default=0),
                         "mean_channel_defects": differences, "overlap": overlap, "target_overlap": target,
                         "pair_calibration_pass": overlap == target})
    admissible = all(family["mean_channel_pass"] and family["pair_calibration_pass"] for family in families)
    numeric = {"bias_at_least_0_0235": original["fit"]["bias"] >= 0.0235,
               "residual_at_most_0_004": original["fit"]["max_residual"] <= 0.004,
               "S256_at_least_0_005": original["polarizations"][-1] >= 0.005}
    return {"generation": 3, "admissible": admissible, "passed": admissible and all(numeric.values()),
            "bias_target": 0.0235, "numeric_checks": numeric, "family_calibrations": families,
            "fit": original["fit"], "S256": original["polarizations"][-1],
            "exact_global_overlap": original["constraints"]["pair_overlap_total"],
            "polarizations": original["polarizations"],
            "probability_space_crosscheck": original["probability_space_crosscheck"],
            "independence": "Tuple-based Pauli implementation and probability-space convolution; no public model import"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    arguments = parser.parse_args()
    try:
        result = check(json.loads(Path(arguments.witness).read_text()))
    except (ValueError, TypeError, OSError) as error:
        result = {"generation": 3, "admissible": False, "passed": False, "reason": str(error)}
    print(json.dumps(result, indent=2, allow_nan=False))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
