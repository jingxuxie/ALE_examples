import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1] / "concept_2"
    generator = np.random.default_rng(907163)
    banks = []
    for index, scale in enumerate((3.6, 4.4, 5.2)):
        fields = np.linspace(-scale, scale, 12) + generator.uniform(-0.12, 0.12, 12)
        fields -= np.mean(fields)
        generator.shuffle(fields)
        banks.append({"id": "bank_" + str(index + 1), "fields": fields.tolist()})
    seed_path = root / "evaluator/hidden/seeds.json"
    seed_path.write_text(json.dumps({"seeds": [None, 19270351, 82947531, 10297513, 59270517]}) + "\n")
    spec = {"generation": 1, "banks": banks, "scales": [0.96, 1.0, 1.04], "jitter": 0.02,
            "perturbation_distribution": "Each labelled field receives independent uniform[-jitter,jitter] noise, identically for both layouts. Each scale uses the same fieldwise noise; no mean subtraction. None denotes no noise.",
            "public_seeds": [None, 74032, 51067], "hidden_draws_per_scale": 5,
            "targets": {"mean_abs_r_difference_max": 0.02, "max_abs_r_difference_max": 0.045,
                        "mean_f_separation_min": 0.28, "min_f_separation_min": 0.24},
            "hidden_seeds_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest()}
    for path in (root / "participant/input/spec.json", root / "evaluator/hidden/spec.json"):
        path.write_text(json.dumps(spec, indent=2) + "\n")
    (root / "status.json").write_text(json.dumps({"concept": "Spectrally matched disorder layouts", "mode": "C_WITNESS_OR_DESIGN_CONSTRUCTION", "status": "awaiting_first_tournament", "generation": 1, "targets": spec["targets"], "passing_solution_known": False}, indent=2) + "\n")


if __name__ == "__main__":
    main()
