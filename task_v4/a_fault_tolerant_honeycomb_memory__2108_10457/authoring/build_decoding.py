import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "authoring" / "deps"), str(ROOT / "authoring" / "upstream" / "src")]
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import numpy as np
import pymatching
import stim
from honeycomb_layout import HoneycombLayout


def write_case(destination, configuration, seed, shots, labels):
    destination.mkdir(parents=True, exist_ok=True)
    original = HoneycombLayout(**configuration).make_circuit()
    circuit = stim.Circuit()
    for instruction in original.flattened():
        if instruction.name == "OBSERVABLE_INCLUDE":
            circuit.append("OBSERVABLE_INCLUDE", instruction.targets_copy(), 0)
        else:
            circuit.append(instruction)
    model = circuit.detector_error_model(decompose_errors=True)
    if circuit.num_observables != 1:
        raise ValueError("one logical observable required")
    circuit.to_file(destination / "circuit.stim")
    model.to_file(destination / "model.dem")
    syndrome, truth = circuit.compile_detector_sampler(seed=seed).sample(shots, separate_observables=True)
    truth = truth[:, 0].astype(np.uint8)
    np.save(destination / "syndromes.npy", syndrome.astype(np.uint8), allow_pickle=False)
    decoder = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
    prediction = decoder.decode_batch(syndrome, enable_correlations=True)[:, 0].astype(np.uint8)
    labels.mkdir(parents=True, exist_ok=True)
    np.save(labels / (destination.name + ".npy"), truth, allow_pickle=False)
    (destination / "metadata.json").write_text(json.dumps(configuration, indent=2) + "\n")
    return prediction, int(np.count_nonzero(prediction != truth))


def main():
    concept = ROOT / "concept_1"
    participant = concept / "participant"
    for directory in ["attempts", "champions", "adversary", "evaluator/hidden"]:
        (concept / directory).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "authoring" / "deps", participant / "workspace", dirs_exist_ok=True)
    hidden = concept / "evaluator" / "hidden"
    families = [("em3", "EM3_v2", [0.006, 0.009, 0.012, 0.014]),
                ("sd6", "SD6", [0.0008, 0.0012, 0.0017, 0.002]),
                ("si1000", "SI1000", [0.0005, 0.0007, 0.0009, 0.0011])]
    manifest = []
    for family_index, (family, style, probabilities) in enumerate(families):
        for case_index in range(4):
            configuration = {"data_width": [8, 8, 12, 12][case_index],
                             "data_height": [12, 18, 12, 18][case_index],
                             "sub_rounds": [18, 24, 36, 42][case_index],
                             "style": style, "obs": "H" if case_index % 2 == 0 else "V",
                             "noise": probabilities[case_index]}
            identifier = f"{family}_{case_index}"
            baseline, count = write_case(hidden / "requests" / identifier, configuration,
                                         951703 + family_index * 8713 + case_index * 13007,
                                         8192, hidden / "labels")
            (hidden / "baseline").mkdir(exist_ok=True)
            np.save(hidden / "baseline" / (identifier + ".npy"), baseline, allow_pickle=False)
            manifest.append({"id": identifier, "family": family, "shots": 8192, "baseline_errors": count})
            print(identifier, count, flush=True)
        configuration = {"data_width": 8, "data_height": 12, "sub_rounds": 12,
                         "style": style, "obs": "H", "noise": probabilities[1]}
        write_case(participant / "input" / f"dev_{family}_h", configuration,
                   1087 + family_index, 2048, participant / "input" / "development_labels")
    (hidden / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    protocol = {"mode": "A", "primary": "baseline_improvement", "core_ratio_max": 0.80,
                "worst_family_ratio_max": 0.95, "paired_sigma_min": 3.0,
                "seconds_per_request": 60, "memory_mib": 4096,
                "baseline": "PyMatching 2.4.0 two-pass correlated matching",
                "stim_version": stim.__version__, "fixed_before_first_attempt": True}
    (concept / "evaluator" / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")


if __name__ == "__main__":
    main()
