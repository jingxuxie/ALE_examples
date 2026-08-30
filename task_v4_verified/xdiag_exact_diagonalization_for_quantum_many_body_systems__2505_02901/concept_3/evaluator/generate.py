import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from physics import LOWER, UPPER, PARAMETER_NAMES, STATES, probabilities


def parameters_for_family(random, family):
    values = LOWER + (UPPER - LOWER) * random.uniform(0.1, 0.9, len(LOWER))
    if family == "smooth":
        values[:6] = random.uniform(0.85, 1.15, 6)
        values[6:11] = random.uniform(-0.16, 0.16, 5)
        values[11] = random.uniform(0.6, 1.2)
        values[12:14] = random.uniform(0.07, 0.18, 2)
    elif family == "frustrated":
        values[:6] = random.uniform(0.65, 1.35, 6)
        values[12:14] = random.uniform(0.33, 0.49, 2)
        values[11] = random.uniform(1.1, 1.6)
    elif family == "field_disorder":
        values[6:11] = random.uniform(0.22, 0.48, 5) * random.choice([-1, 1])
        values[:6] = random.uniform(0.57, 1.15, 6)
        values[11] = random.uniform(0.35, 1.0)
    return values


def main():
    config = {
        "nsites": 6, "nup": 3, "parameter_names": PARAMETER_NAMES,
        "lower": LOWER.tolist(), "upper": UPPER.tolist(),
        "query_budget": 18, "shots": 2048, "cpu_seconds": 120,
        "wall_seconds": 180, "memory_mib": 2048, "threads": 4,
        "target_core_score": 0.970, "target_worst_family_score": 0.950,
    }
    (ROOT / "participant/input/config.json").write_text(json.dumps(config, indent=2) + "\n")
    random = np.random.default_rng(85142068)
    cases = []
    for family in ("smooth", "frustrated", "field_disorder"):
        for case_index in range(4):
            parameters = parameters_for_family(random, family)
            cases.append({"id": f"device-{int(random.integers(10000000, 99999999))}", "family": family, "parameters": parameters.tolist(), "noise_seed": int(random.integers(2**31))})
    (ROOT / "evaluator/hidden/devices.json").write_text(json.dumps(cases, indent=2) + "\n")
    public_random = np.random.default_rng(5939011)
    examples = []
    for family in ("smooth", "frustrated", "field_disorder"):
        parameters = parameters_for_family(public_random, family)
        experiment = {"type": "query", "preparation": int(STATES[7]), "time": 1.2, "phases": [0.3, 0.1, -0.2, 0.4, -0.1, 0.0]}
        examples.append({"family": family, "parameters": parameters.tolist(), "experiment": experiment, "probabilities": probabilities(parameters, experiment).tolist()})
    (ROOT / "participant/input/development.json").write_text(json.dumps(examples, indent=2) + "\n")
    status = {"name": "Active interacting-spin spectroscopy", "verification_mode": "E", "status": "built", "target": {"core_score": 0.970, "worst_family_score": 0.950}, "ratchet_generations": 0, "solvability": "unknown", "hidden_devices": len(cases)}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    main()
