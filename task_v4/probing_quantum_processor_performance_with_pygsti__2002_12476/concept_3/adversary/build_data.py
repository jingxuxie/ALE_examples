import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from simulator import predict_devices, sample_parameters


FAMILIES = ["germ_repetition", "refocusing", "burst_switching", "drift_transfer"]
GERMS = [[0], [1], [2], [3], [4], [1, 3], [1, 4], [1, 3, 2, 4],
         [1, 0, 2, 0], [3, 0, 4, 0], [1, 1, 3, 3], [1, 3, 3],
         [1, 1, 1, 1], [3, 3, 3, 3], [1, 2], [3, 4]]


def circuit(generator, family, depth):
    if family == "random":
        return generator.integers(0, 5, size=depth).tolist()
    prefix = generator.integers(0, 5, size=int(generator.integers(0, 4))).tolist()
    suffix = generator.integers(0, 5, size=int(generator.integers(0, 4))).tolist()
    budget = max(1, depth - len(prefix) - len(suffix))
    if family == "drift_transfer":
        family = FAMILIES[int(generator.integers(0, 3))]
    if family == "germ_repetition":
        if generator.random() < 0.75:
            motif = GERMS[int(generator.integers(len(GERMS)))]
        else:
            motif = generator.integers(0, 5, size=int(generator.integers(2, 7))).tolist()
        middle = motif * max(1, budget // len(motif))
    elif family == "refocusing":
        gap = int(generator.integers(1, min(13, max(2, budget // 4))))
        pulse = int(generator.choice([1, 2, 3, 4]))
        inverse = {1: 2, 2: 1, 3: 4, 4: 3}[pulse]
        motif = [0] * gap + [pulse, pulse] + [0] * gap + [inverse, inverse]
        middle = motif * max(1, budget // len(motif))
    elif family == "burst_switching":
        middle = []
        previous = -1
        while len(middle) < budget:
            choices = [gate for gate in range(5) if gate != previous]
            gate = int(generator.choice(choices))
            run = int(generator.integers(4, min(49, max(5, budget // 2 + 1))))
            middle.extend([gate] * run)
            previous = gate
        middle = middle[:budget]
    else:
        raise ValueError(f"Unknown family: {family}")
    return (prefix + middle + suffix)[:depth]


def pack(records):
    count = len(records)
    maximum = max(len(record["gates"]) for record in records)
    gates = np.full((count, maximum), -1, dtype=np.int8)
    for row, record in enumerate(records):
        gates[row, :len(record["gates"])] = record["gates"]
    return {
        "ids": np.arange(count, dtype=np.int64),
        "device": np.array([record["device"] for record in records], dtype=np.int8),
        "time": np.array([record["time"] for record in records]),
        "preparation": np.array([record["preparation"] for record in records], dtype=np.int8),
        "measurement": np.array([record["measurement"] for record in records], dtype=np.int8),
        "length": np.array([len(record["gates"]) for record in records], dtype=np.int16),
        "gates": gates,
        "family": np.array([record["family"] for record in records], dtype="U20"),
    }


def record_key(record):
    return (record["device"], record["time"], record["preparation"],
            record["measurement"], tuple(record["gates"]))


def make_records(generator, split, seen, per_cell=None):
    records = []
    for device in range(4):
        if split == "train":
            for time_value in np.linspace(0., 1., 9):
                for word in [[], [0], [1], [2], [3], [4]]:
                    for preparation in range(6):
                        for measurement in range(3):
                            record = dict(device=device, time=float(time_value), preparation=preparation,
                                          measurement=measurement, gates=word, family="calibration")
                            seen.add(record_key(record))
                            records.append(record)
            family_sequence = (["random"] + FAMILIES) * (6144 // 5 + 1)
            family_sequence = family_sequence[:6144]
        else:
            count = per_cell if per_cell is not None else (128 if split == "development" else 512)
            family_sequence = [family for family in FAMILIES for row in range(count)]
        for row, family in enumerate(family_sequence):
            while True:
                if split == "train":
                    possible = [112, 128, 160, 192] if row % 4 == 0 else [4, 8, 12, 16, 24, 32, 48, 64, 80, 96]
                    time_value = float(generator.integers(0, 17) / 16.)
                else:
                    possible = [144, 160, 192, 224, 256, 288] if split == "development" else [288, 320, 384, 448, 512]
                    time_value = float(generator.uniform(0.02, 0.98))
                depth = int(generator.choice(possible))
                record = dict(device=device, time=time_value, preparation=int(generator.integers(6)),
                              measurement=int(generator.integers(3)), gates=circuit(generator, family, depth),
                              family=family)
                key = record_key(record)
                if key not in seen:
                    seen.add(key)
                    records.append(record)
                    break
    generator.shuffle(records)
    return records


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    arguments = parser.parse_args()
    private = ROOT / "evaluator" / "hidden"
    public = ROOT / "participant" / "input"
    if (private / "truth.npz").exists() and not arguments.rebuild:
        parser.error("Data already exist; do not regenerate a launched task")
    started = time.perf_counter()
    seeds = {"parameters": 874140639, "train_queries": 441797071, "development_queries": 741683649,
             "test_queries": 816352731, "train_counts": 503814099, "development_counts": 928508451}
    parameters = np.stack([sample_parameters(np.random.default_rng(seeds["parameters"] + device))
                           for device in range(4)])
    np.savez_compressed(private / "parameters.npz", parameters=parameters)
    write_json(private / "seeds.json", seeds)
    protocol = json.loads((public / "protocol.json").read_text())
    write_json(private / "protocol.json", protocol)
    seen = set()
    summaries = {}
    for split in ["train", "development", "test"]:
        generator = np.random.default_rng(seeds[split + "_queries"])
        data = pack(make_records(generator, split, seen))
        truth = predict_devices(parameters, data)
        if split != "test":
            count_generator = np.random.default_rng(seeds[split + "_counts"])
            if split == "train":
                shots = np.where(data["family"] == "calibration", 32768,
                                 count_generator.choice([8192, 16384], len(truth)))
            else:
                shots = np.full(len(truth), 65536)
            data["shots"] = shots.astype(np.int64)
            data["count_one"] = count_generator.binomial(shots, truth).astype(np.int64)
        filename = "queries.npz" if split == "test" else split + ".npz"
        np.savez_compressed(public / filename, **data)
        private_name = "truth.npz" if split == "test" else split + "_truth.npz"
        np.savez_compressed(private / private_name, ids=data["ids"], family=data["family"],
                            device=data["device"], p1=truth)
        summaries[split] = {
            "rows": len(truth), "minimum_length": int(data["length"].min()),
            "maximum_length": int(data["length"].max()),
            "family_counts": {family: int(np.sum(data["family"] == family)) for family in np.unique(data["family"])},
            "probability_range": [float(truth.min()), float(truth.max())],
            "mean_shots": float(np.mean(data["shots"])) if split != "test" else None,
        }
        print(split, summaries[split], flush=True)
    integrity = {name: hashlib.sha256((private / name).read_bytes()).hexdigest()
                 for name in ["truth.npz", "protocol.json"]}
    write_json(private / "integrity.json", integrity)
    manifest = {name: hashlib.sha256((public / name).read_bytes()).hexdigest()
                for name in ["train.npz", "development.npz", "queries.npz", "protocol.json", "PHYSICS.md", "FORMAT.md"]}
    write_json(public / "manifest.json", manifest)
    summaries["runtime_seconds"] = time.perf_counter() - started
    summaries["separate_seeds_for_queries_parameters_and_counts"] = True
    summaries["exact_record_split_overlap"] = 0
    write_json(ROOT / "adversary" / "dataset_summary.json", summaries)


if __name__ == "__main__":
    main()
