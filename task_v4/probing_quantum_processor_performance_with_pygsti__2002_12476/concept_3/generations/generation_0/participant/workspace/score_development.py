import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    document = json.loads(arguments.submission.read_text())
    identifiers = document["ids"]
    if len(identifiers) != len(data["ids"]) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Wrong or duplicate development IDs")
    mapping = dict(zip(identifiers, document["p1"]))
    predictions = np.array([mapping[int(identifier)] for identifier in data["ids"]], dtype=float)
    if not np.all(np.isfinite(predictions)) or np.any(predictions < 0.) or np.any(predictions > 1.):
        raise ValueError("Probabilities must be finite and in [0,1]")
    observed = data["count_one"] / data["shots"]
    noise = observed * (1. - observed) / (data["shots"] - 1.)
    output = {}
    for family in np.unique(data["family"]):
        mask = data["family"] == family
        mse = float(np.mean((predictions[mask] - observed[mask]) ** 2))
        noise_mse = float(np.mean(noise[mask]))
        output[str(family)] = {"observed_rmse": float(np.sqrt(mse)),
                               "estimated_shot_noise_rmse": float(np.sqrt(noise_mse)),
                               "noise_corrected_rmse": float(np.sqrt(max(0., mse - noise_mse))),
                               "rows": int(np.sum(mask))}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
