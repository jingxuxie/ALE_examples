import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "participant/baseline"))
from channel import marginals
from solve import solve
sys.path.insert(0, str(ROOT / "evaluator"))
from exact import characteristic_distribution, score_answer
from audit_structure import rank


def instance(seed, family):
    generator = random.Random(seed)
    detectors = 18
    channels = []
    base_signatures = []
    for index in range(22):
        detector_signature = generator.getrandbits(detectors)
        logical = generator.random() < 0.50
        base_signatures.append(detector_signature | (int(logical) << detectors))
    detector_rank = rank([signature & ((1 << detectors) - 1) for signature in base_signatures])
    candidate = 0
    while rank(base_signatures) <= detector_rank:
        base_signatures[candidate] ^= 1 << detectors
        candidate += 1
    regimes = 5
    for index in range(22):
        count = {"biased": 1, "correlated": 3, "drifting": 2}[family]
        signatures = [base_signatures[index]]
        for branch in range(count - 1):
            neighbor = (index + generator.randint(1, 21)) % 22
            signatures.append(generator.getrandbits(detectors + 1) if family == "correlated" else base_signatures[index] ^ base_signatures[neighbor])
        probabilities = []
        weights = [generator.uniform(0.2, 1.0) for branch in signatures]
        for regime in range(regimes):
            activation = generator.uniform(0.015, 0.09)
            if index % regimes == regime:
                activation *= {"biased": 4.5, "correlated": 3.5, "drifting": 4.0}[family]
            shifted = [weight * generator.uniform(0.4, 1.8) for weight in weights]
            probabilities.append([round(activation * weight / sum(shifted), 12) for weight in shifted])
        channels.append({"signatures": signatures, "probabilities": probabilities})
    taps = [1 << index for index in range(detectors)]
    while len(taps) < 38:
        mask = generator.getrandbits(detectors)
        if mask and mask not in taps:
            taps.append(mask)
    generator.shuffle(taps)
    return {"schema": "detector-compression/v1", "detectors": detectors, "taps": taps, "budget": 6,
            "regimes": ["regime_" + str(index) for index in range(regimes)], "channels": channels}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    results = []
    validation = []
    for family_index, family in enumerate(("biased", "correlated", "drifting")):
        for split, count, start in (("public", 1, 739021), ("hidden", 2, 847191)):
            for offset in range(count):
                seed = start + family_index * 1003 + offset * 7213
                model = instance(seed, family)
                name = family + "_" + str(offset)
                directory = ROOT / ("participant/input" if split == "public" else "evaluator/hidden/instances")
                path = directory / (name + ".json")
                write_json(path, model)
                started = time.monotonic()
                answer = solve(model)
                elapsed = time.monotonic() - started
                scores = score_answer(model, answer)
                direct = marginals(model, answer["selected"])
                spectral = characteristic_distribution(model, answer["selected"])
                maximum_difference = float(np.max(np.abs(direct - spectral)))
                if maximum_difference > 2e-12:
                    raise RuntimeError("independent probability engines disagree")
                record = {"name": name, "family": family, "split": split, "baseline": scores,
                          "baseline_seconds": elapsed, "baseline_answer": answer,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                results.append(record)
                validation.append({"name": split + "/" + name, "engine_difference": maximum_difference})
                print(split, name, scores["worst_risk"], elapsed, flush=True)
    write_json(ROOT / "evaluator/hidden/baselines.json", [record for record in results if record["split"] == "hidden"])
    write_json(ROOT / "adversary/baseline_validation.json", {"instances": results, "crosschecks": validation})
    write_json(ROOT / "participant/baseline/scores.json", [record for record in results if record["split"] == "public"])


if __name__ == "__main__":
    main()
