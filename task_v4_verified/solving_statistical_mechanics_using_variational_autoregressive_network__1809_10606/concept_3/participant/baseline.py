"""Nearest-temperature empirical joint prediction with local field reweighting."""

import argparse
import json
from pathlib import Path

import numpy as np


def predict(input_dir):
    input_dir = Path(input_dir)
    spec = json.loads((input_dir / "model.json").read_text())
    queries = json.loads((input_dir / "queries.json").read_text())
    with np.load(input_dir / "train.npz", allow_pickle=False) as training:
        configurations = training["visible_spins"]
        betas = training["betas"]
    lookup = {spin: index for index, spin in enumerate(spec["visible_indices"])}
    states = 2 * ((np.arange(64)[:, None] >> np.arange(6)) & 1) - 1
    predictions = []
    for query in queries:
        condition = int(np.argmin(np.abs(betas - query["beta"])))
        selected = configurations[condition][:, [lookup[spin] for spin in query["readout"]]]
        codes = ((selected + 1) // 2) @ (1 << np.arange(6))
        probabilities = np.bincount(codes, minlength=64).astype(np.float64) + 0.5
        correction = np.zeros(64)
        for spin, amplitude in zip(query["field_indices"], query["field_values"]):
            if spin in query["readout"]:
                correction += amplitude * states[:, query["readout"].index(spin)]
        probabilities *= np.exp(query["beta"] * correction)
        predictions.append(probabilities / probabilities.sum())
    return np.asarray(predictions, dtype="<f8"), np.asarray([query["id"] for query in queries], dtype="<U24")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "input")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    probabilities, query_ids = predict(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez(args.output / "predictions.npz", probabilities=probabilities, query_ids=query_ids)


if __name__ == "__main__":
    main()
