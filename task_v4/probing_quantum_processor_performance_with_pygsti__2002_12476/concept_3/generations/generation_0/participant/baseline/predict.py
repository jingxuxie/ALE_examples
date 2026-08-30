import argparse
import json
import time
from pathlib import Path

import numpy as np


PREPARATIONS = 0.985 * np.array([[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.],
                               [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]])


def load_data(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def fit_markov_maps(training):
    maps = np.zeros((4, 5, 3, 3))
    offsets = np.zeros((4, 5, 3))
    for device in range(4):
        for gate in range(5):
            selected = ((training["device"] == device) & (training["length"] == 1)
                        & (training["gates"][:, 0] == gate) & (training["family"] == "calibration"))
            preparations = training["preparation"][selected]
            measurements = training["measurement"][selected]
            counts = training["count_one"][selected]
            shots = training["shots"][selected]
            expectation = 1. - 2. * (counts / shots - 0.008) / 0.979
            design = np.column_stack([PREPARATIONS[preparations], np.ones(len(preparations))])
            for axis in range(3):
                mask = measurements == axis
                weights = np.sqrt(shots[mask])
                solution = np.linalg.lstsq(design[mask] * weights[:, None],
                                           expectation[mask] * weights, rcond=None)[0]
                maps[device, gate, axis] = solution[:3]
                offsets[device, gate, axis] = solution[3]
            left, singular, right = np.linalg.svd(maps[device, gate])
            radius = max(0.9, 1. - np.linalg.norm(offsets[device, gate]))
            maps[device, gate] = (left * np.minimum(singular, radius)) @ right
    return maps, offsets


def predict(maps, offsets, data):
    bloch = PREPARATIONS[data["preparation"]].copy()
    for position in range(int(np.max(data["length"]))):
        selected = data["length"] > position
        devices = data["device"][selected]
        gates = data["gates"][selected, position]
        bloch[selected] = np.einsum("nij,nj->ni", maps[devices, gates], bloch[selected]) + offsets[devices, gates]
    expectation = bloch[np.arange(len(bloch)), data["measurement"]]
    return np.clip(0.008 + 0.979 * (1. - expectation) / 2., 0., 1.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["queries", "development", "train"], default="queries")
    arguments = parser.parse_args()
    started = time.perf_counter()
    training = load_data(arguments.input / "train.npz")
    queries = load_data(arguments.input / (arguments.split + ".npz"))
    maps, offsets = fit_markov_maps(training)
    predictions = predict(maps, offsets, queries)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps({"ids": queries["ids"].tolist(), "p1": predictions.tolist()},
                                          allow_nan=False) + "\n")
    print(json.dumps({"rows": len(predictions), "runtime_seconds": time.perf_counter() - started,
                      "model": "time-averaged single-gate affine tomography"}))


if __name__ == "__main__":
    main()
