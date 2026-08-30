import itertools
import json
from pathlib import Path
import random
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from exact import characteristic_distribution, score_answer
sys.path.insert(0, str(ROOT / "participant/workspace"))
from channel import marginals
sys.path.insert(0, str(ROOT.parent / "authoring/vendor"))
import stim


def native_circuit(model, regime):
    circuit = stim.Circuit()
    for channel in model["channels"]:
        remainder = 1.0
        for index, (signature, probability) in enumerate(zip(channel["signatures"], channel["probabilities"][regime])):
            targets = [stim.target_x(qubit) for qubit in range(model["detectors"] + 1) if signature >> qubit & 1]
            circuit.append("E" if index == 0 else "ELSE_CORRELATED_ERROR", targets, probability / remainder)
            remainder -= probability
    circuit.append("M", list(range(model["detectors"] + 1)))
    for detector in range(model["detectors"]):
        circuit.append("DETECTOR", [stim.target_rec(detector - model["detectors"] - 1)])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    return circuit


def main():
    rng = random.Random(81297)
    differences = []
    for trial in range(60):
        model = {"detectors": 4, "taps": rng.sample(list(range(1, 16)), 6), "budget": 4,
                 "regimes": ["a", "b"], "channels": []}
        for channel in range(4):
            model["channels"].append({"signatures": rng.sample(list(range(1, 32)), 3),
                                      "probabilities": [[0.1, 0.2, 0.05], [0.05, 0.03, 0.25]]})
        selected = sorted(rng.sample(range(6), 4))
        projected = np.zeros((2, 16, 2))
        for choices in itertools.product(range(4), repeat=4):
            signature = 0
            mass = np.ones(2)
            for choice, channel in zip(choices, model["channels"]):
                if choice:
                    signature ^= channel["signatures"][choice - 1]
                    mass *= [probabilities[choice - 1] for probabilities in channel["probabilities"]]
                else:
                    mass *= [1 - sum(probabilities) for probabilities in channel["probabilities"]]
            syndrome = sum(((signature & model["taps"][tap]).bit_count() & 1) << index for index, tap in enumerate(selected))
            projected[:, syndrome, signature >> 4] += mass
        spectral = characteristic_distribution(model, selected)
        direct = marginals(model, selected)
        differences.append(float(max(np.max(np.abs(projected - spectral)), np.max(np.abs(direct - spectral)))))
    if max(differences) > 1e-12:
        raise RuntimeError("exact independent enumeration failed")
    physical = []
    for path in sorted((ROOT / "evaluator/hidden/instances").glob("*.json")):
        model = json.loads(path.read_text())
        circuit = native_circuit(model, 0)
        samples = circuit.compile_sampler(seed=58117).sample(shots=200000).astype(np.uint8)
        selected = list(range(6))
        pattern = np.zeros(len(samples), dtype=np.int64)
        for position, tap in enumerate(selected):
            indices = [index for index in range(model["detectors"]) if model["taps"][tap] >> index & 1]
            values = np.bitwise_xor.reduce(samples[:, indices], axis=1)
            pattern |= values.astype(np.int64) << position
        pattern |= samples[:, -1].astype(np.int64) << 6
        measured = np.bincount(pattern, minlength=128).reshape(2, 64).T / len(samples)
        expected = characteristic_distribution(model, selected)[0]
        standard_error = np.sqrt(np.maximum(expected * (1 - expected), 1 / len(samples)) / len(samples))
        maximum_z = float(np.max(np.abs(measured - expected) / standard_error))
        if maximum_z > 7:
            raise RuntimeError("native Stim disagrees statistically")
        destination = ROOT / "adversary/native_models" / (path.stem + ".stim")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(str(circuit))
        physical.append({"instance": path.stem, "native_maximum_z": maximum_z, "shots": len(samples)})
    model = json.loads(next((ROOT / "evaluator/hidden/instances").glob("*.json")).read_text())
    malformed = [{"selected": [0, 0], "correction": [0] * 4}, {"selected": [-1], "correction": [0, 1]},
                 {"selected": [], "correction": [0.0]}, {"selected": list(range(8)), "correction": [0] * 256},
                 {"selected": [], "correction": [float("nan")]}, {"selected": [], "correction": [True]}]
    rejected = 0
    for answer in malformed:
        try:
            score_answer(model, answer)
        except ValueError:
            rejected += 1
    if rejected != len(malformed):
        raise RuntimeError("malformed answer accepted")
    report = {"passed": True, "exact_enumeration_trials": len(differences), "maximum_difference": max(differences),
              "malformed_rejected": rejected, "stim_version": stim.__version__, "native_models": physical}
    (ROOT / "adversary/probability_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
