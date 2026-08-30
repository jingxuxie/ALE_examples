import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
sys.path.insert(0, str(CONCEPT / "adversary"))
sys.path.insert(0, str(CONCEPT / "evaluator" / "hidden"))
sys.path.insert(0, str(HERE / "solver"))
from build_data import make_records, pack
from simulator import predict as independent_predict, sample_parameters
import model


CORNER_NAMES = ["slow_balanced_strong_memory", "fast_asymmetric_environment", "long_memory_coherent_extremes",
                "minimum_damping_strong_drift", "nearly_weak_memory", "almost_constant_drift",
                "balanced_signed_cancellation", "opposed_drift_quadratures"]


def create_parameters(seed, campaign_kind):
    generator = np.random.default_rng(seed)
    parameters = np.stack([sample_parameters(generator) for device in range(4)])
    regimes = ["independent_uniform"] * 4
    if campaign_kind == "uniform":
        return parameters, regimes
    if campaign_kind == "hypercube":
        signs = generator.choice([-1., 1.], size=(4, 54))
        parameters = model.CENTER + model.SCALE * signs * generator.uniform(0.92, 0.9995, size=(4, 54))
        assert np.all(parameters >= model.LOWER) and np.all(parameters <= model.UPPER)
        return parameters, ["joint_parameter_box_corner"] * 4
    offset = int(campaign_kind.split("_")[-1]) * 4
    for device in range(4):
        values = parameters[device]
        index = (offset + device) % len(CORNER_NAMES)
        regimes[device] = CORNER_NAMES[index]
        signs = generator.choice([-1., 1.], size=54)
        if index == 0:
            values[17] = 0.0618
            values[[24, 25]] = [0.969, 0.967]
            values[[33, 37]] = [-5.79, -5.79]
            values[[34, 38]] = [-0.79, -0.79]
            values[22:24] = signs[22:24] * 0.0695
            values[41:44] *= 0.03
        elif index == 1:
            values[[33, 37]] = [-3.81, -5.79]
            values[[34, 38]] = [0.79, -0.79]
            values[[35, 39]] = [1.09, -1.09]
            values[[36, 40]] = [0.49, -0.49]
            values[17] = 0.0618
            values[41:44] = [0.79, 0.99, 0.69]
        elif index == 2:
            values[:15] = signs[:15] * 0.0179
            values[18:22] = signs[18:22] * 0.0298
            values[22:24] = signs[22:24] * 0.0695
            values[[24, 25]] = [0.9698, 0.9692]
            values[17] = 0.0618
        elif index == 3:
            values[44:54] = 0.0001005
            values[26:32] = signs[26:32] * np.array([0.00895, 0.00895, 0.0179] * 2)
            values[32] = 1.499
            values[17] = 0.0618
        elif index == 4:
            values[18:24] *= 0.001
            values[[24, 25]] = [0.9698, 0.8202]
            values[32] = 0.8005
        elif index == 5:
            values[26:32] *= 0.001
            values[32] = 1.4995
            values[17] = 0.0281
            values[[33, 37]] = [-3.81, -3.81]
        elif index == 6:
            values[18:22] = [0.0297, -0.0297, -0.0297, 0.0297]
            values[22:24] = [0.0697, -0.0697]
            values[[24, 25]] = [0.9695, 0.9695]
            values[41:44] = 0.
            values[[33, 37]] = [-5.79, -5.79]
            values[[34, 38]] = 0.
        elif index == 7:
            values[26:29] = [0.0089, -0.0089, 0.0178]
            values[29:32] = [-0.0089, 0.0089, -0.0178]
            values[32] = 0.8002
            values[15:18] = [0.0079, -0.0079, 0.0619]
    assert np.all(parameters >= model.LOWER) and np.all(parameters <= model.UPPER)
    return parameters, regimes


def generate(campaign_index, campaign_kind):
    directory = HERE / "campaigns" / f"campaign_{campaign_index:02d}"
    public = directory / "input"
    private = directory / "private"
    if (directory / "metadata.json").exists():
        return
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    for name in ["output", "tmp"]:
        (directory / name).mkdir(exist_ok=True)
    started = time.monotonic()
    seed = 912627100 + 1973 * campaign_index
    parameters, regimes = create_parameters(seed, campaign_kind)
    np.savez_compressed(private / "parameters.npz", parameters=parameters)
    seen = set()
    audits = []
    sizes = {}
    for split_index, split in enumerate(["train", "development", "test"]):
        generator = np.random.default_rng(seed + 111 + 43 * split_index)
        data = pack(make_records(generator, split, seen))
        probabilities = np.empty(len(data["ids"]))
        for device in range(4):
            selected = data["device"] == device
            subset = model.select(data, selected)
            probabilities[selected] = model.predict(parameters[device], subset, threads=1)
            chosen = generator.choice(len(subset["ids"]), 24, replace=False)
            independent_subset = model.select(subset, chosen)
            error = float(np.max(np.abs(independent_predict(parameters[device], independent_subset)
                                        - model.predict(parameters[device], independent_subset, threads=1))))
            assert error < 1e-10
            audits.append({"device": device, "split": split, "rows": 24, "max_native_independent_difference": error})
        assert np.all((probabilities > 0.) & (probabilities < 1.))
        if split != "test":
            counts_generator = np.random.default_rng(seed + 5911 + 89 * split_index)
            shots = (np.where(data["family"] == "calibration", 32768,
                              counts_generator.choice([8192, 16384], len(probabilities)))
                     if split == "train" else np.full(len(probabilities), 65536))
            data["shots"] = shots.astype(np.int64)
            data["count_one"] = counts_generator.binomial(shots, probabilities).astype(np.int64)
        name = "queries" if split == "test" else split
        np.savez_compressed(public / (name + ".npz"), **data)
        np.savez_compressed(private / (name + "_truth.npz"), ids=data["ids"], family=data["family"],
                            device=data["device"], p1=probabilities)
        sizes[split] = len(probabilities)
    metadata = {"campaign_index": campaign_index, "kind": campaign_kind, "regimes": regimes,
                "seed": seed, "query_and_count_seeds_independent_of_parameters": True,
                "all_parameters_inside_original_ranges": True, "original_acquisition_generator_unchanged": True,
                "rows": sizes, "independent_physics_checks": audits,
                "parameter_sha256": hashlib.sha256((private / "parameters.npz").read_bytes()).hexdigest(),
                "runtime_seconds": time.monotonic() - started}
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("BUILT", campaign_index, campaign_kind, "seconds", metadata["runtime_seconds"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=int, required=True)
    parser.add_argument("--kind", default="uniform")
    arguments = parser.parse_args()
    generate(arguments.campaign, arguments.kind)


if __name__ == "__main__":
    main()
