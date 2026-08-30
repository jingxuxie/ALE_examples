import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from screen import FAMILIES, SPEC, encode, measure, probabilities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--trials", type=int, default=64)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    generator = np.random.default_rng(args.seed)
    best = {"version": 1, "gate_parameters": [[0.] * 5 for index in range(3)], "circuit": "IXY" * 21 + "I"}
    best_score = measure(best)["worst_family_score"]
    calibration = encode(sum(FAMILIES.values(), []))
    for trial in range(args.trials):
        parameters = generator.normal(0, .006, (3, 5))
        parameters[:, 0] = generator.uniform(-np.pi, np.pi, 3)
        truth, prediction, leakage = probabilities(parameters, calibration)
        parameters[:, 1:] *= min(1., np.sqrt(.003 / max(abs(truth - prediction))))
        words = ["".join(generator.choice(list("IXY"), 64)) for index in range(64)]
        truth, prediction, leakage = probabilities(parameters, encode(words))
        for index in np.argsort(-abs(truth - prediction))[:3]:
            witness = {"version": 1, "gate_parameters": parameters.tolist(), "circuit": words[index]}
            try:
                result = measure(witness)
            except ValueError:
                continue
            eligible = result["calibration_accepted"] and all(
                scenario["final_leakage"] <= SPEC["heldout_max_final_leakage"] for scenario in result["scenarios"])
            if eligible and result["worst_family_score"] > best_score:
                best, best_score = witness, result["worst_family_score"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(best, indent=2, allow_nan=False) + "\n")
    print(json.dumps(measure(best), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
