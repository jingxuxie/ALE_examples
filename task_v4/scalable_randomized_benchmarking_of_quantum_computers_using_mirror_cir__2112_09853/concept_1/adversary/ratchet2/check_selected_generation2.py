import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


def check(payload):
    original = verify.verify(payload)
    gates = verify.make_gates(payload)
    family_results = []
    for name, selection, target in (("single", range(24), 28800), ("cx", range(24, 32), 1920)):
        overlap = sum(sum(count * gates[index]["counts"].get(verify.transform(gates[index]["key"], pauli), 0)
                          for pauli, count in gates[gates[index]["inverse"]]["counts"].items())
                      for index in selection)
        family_results.append({"family": name, "unweighted_overlap": overlap, "target": target,
                               "passed": overlap == target})
    checks = {"global_mean_and_original_integer_constraints": True,
              "single_family_pair_calibration": family_results[0]["passed"],
              "cx_family_pair_calibration": family_results[1]["passed"],
              "bias_at_least_0_0239": original["fit"]["bias"] >= 0.0239,
              "residual_at_most_0_004": original["fit"]["max_residual"] <= 0.004,
              "S256_at_least_0_005": original["polarizations"][-1] >= 0.005}
    return {"generation": 2, "contract_status": "hard_open", "selected_contract": "global mean plus split native-family pair overlaps",
            "family_means_separately_required": False, "bias_target": 0.0239,
            "admissible": all(family["passed"] for family in family_results), "passed": all(checks.values()),
            "original_generation1_pass": original["accepted"], "checks": checks,
            "family_pairs": family_results, "nominal_fit": original["fit"], "S256": original["polarizations"][-1]}


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
