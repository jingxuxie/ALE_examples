import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np


PENDING = Path(__file__).resolve().parent
sys.path.insert(0, str(PENDING / "evaluator"))
from _physics import EliashbergSolver, json_write, load_instance, read_artifact
from evaluate import evaluate


def main():
    started = time.process_time()
    output = PENDING / "mixing_sanity_probe"
    output.mkdir(exist_ok=True)
    instance = load_instance(PENDING / "participant/input")
    pairs = []
    for family in ("compressed_spectrum", "independent_branch_0"):
        artifact = PENDING / "champion_replays" / ("oracle_middle_cross_45__" + family) / "output/witness.npz"
        pairs.append(read_artifact(artifact, instance["config"]))
    fractions = np.linspace(0., 1., 41)
    kernels = np.array([[(1 - fraction) * pairs[0][index] + fraction * pairs[1][index]
                         for fraction in fractions] for index in range(2)])
    temperatures = np.zeros((2, len(fractions), len(instance["config"]["families"])))
    for family_index, family in enumerate(instance["config"]["families"]):
        solver = EliashbergSolver(instance["weights"], instance["row_sums"],
                                 instance["energies_mev"] * np.asarray(family["energy_factors"]), instance["config"])
        for endpoint_index in range(2):
            for fraction_index, modes in enumerate(kernels[endpoint_index]):
                temperatures[endpoint_index, fraction_index, family_index] = solver.critical_temperature(modes, 48)["tc_kelvin"]
    coarse_ratios = np.min(temperatures[1, :, None, :] / temperatures[0, None, :, :], axis=2)
    high_index, low_index = np.unravel_index(np.argmax(coarse_ratios), coarse_ratios.shape)
    artifact = output / "witness.npz"
    with artifact.open("wb") as stream:
        np.savez_compressed(stream, kernels=np.stack([kernels[0, low_index], kernels[1, high_index]]))
    result = evaluate(artifact, output / "evaluation.json", output / "audit.json")
    summary = {
        "purpose": "Hardness sanity check only: this adds a new two-parameter interpolation search and is NOT the unchanged champion algorithm.",
        "coarse_positive_count": 48,
        "fractions_per_endpoint": len(fractions),
        "high_independent_fraction": float(fractions[high_index]),
        "low_independent_fraction": float(fractions[low_index]),
        "coarse_ratio": float(coarse_ratios[high_index, low_index]),
        "exact_ratio": result["score"],
        "valid": result["valid"],
        "admissible": result["admissible"],
        "cpu_seconds": time.process_time() - started,
        "target_ratio_unchanged": 1.09,
        "not_an_actual_champion_replay": True,
    }
    json_write(output / "summary.json", summary)
    json_write(output / "landscape.json", {
        "fractions": fractions.tolist(), "temperatures": temperatures.tolist(),
        "coarse_ratios": coarse_ratios.tolist(),
    })
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
