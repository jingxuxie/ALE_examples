"""NumPy-only amortized inverse trained exclusively on new simulations."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import expit


ROOT = Path(__file__).resolve().parent


def coordinates(observed, sigma, projection):
    standardized = observed / projection["reference_sigma"]
    whitened = np.empty_like(standardized)
    whitened[..., 0] = standardized[..., 0]
    whitened[..., 1:] = (standardized[..., 1:] - .4 * standardized[..., :-1]) / np.sqrt(.84)
    flat = whitened.reshape(len(observed), -1)
    compressed = (flat - projection["center"]) @ projection["basis"].T / projection["scale"]
    relative_noise = sigma[:, 0, 0, 0] / projection["reference_sigma"][0, 0, 0]
    return np.column_stack((compressed, np.log(relative_noise) / np.log(2))).astype(np.float32)


def network_prediction(features, network, bands):
    values = features
    layers = int(network["layers"])
    for index in range(layers):
        values = values @ network[f"weight_{index}"].T + network[f"bias_{index}"]
        if index + 1 < layers:
            values = values * expit(values)
    values = values.reshape(len(features), bands, 14).astype(np.float64)
    values -= values.max(axis=-1, keepdims=True)
    masses = np.exp(values)
    return masses / masses.sum(axis=-1, keepdims=True)


def predict(observed, sigma, sheet_count, selection=None):
    if selection is None:
        selection = json.loads((ROOT / "selection.json").read_text())
    prediction = np.zeros((len(observed), 3, 14))
    for bands in (2, 3):
        selected = sheet_count == bands
        if not np.any(selected):
            continue
        with np.load(ROOT / f"projection_{bands}.npz", allow_pickle=False) as archive:
            projection = {key: archive[key] for key in archive.files}
        features = coordinates(observed[selected], sigma[selected], projection)
        models = selection["models"][str(bands)]
        for name in models:
            with np.load(ROOT / name, allow_pickle=False) as archive:
                network = {key: archive[key] for key in archive.files}
            prediction[selected, :bands] += network_prediction(features, network, bands) / len(models)
        prediction[selected, :bands] /= prediction[selected, :bands].sum(axis=-1, keepdims=True)
    return prediction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = predict(archive["observed"], archive["sigma"], archive["sheet_count"])
    np.savez_compressed(arguments.output, spectral_mass=result)


if __name__ == "__main__":
    main()
