"""Noise-aware, covariance-regularized continuation with a local prior."""

import argparse
import os
from pathlib import Path

import numpy as np
from scipy.linalg import svd


def public_directory():
    supplied = os.environ.get("ALE_PUBLIC_INPUT")
    return Path(supplied) if supplied else Path(__file__).resolve().parents[1] / "input"


def transform(values, sigma, correlation):
    standardized = values / sigma
    transformed = np.empty_like(standardized)
    transformed[..., 0] = standardized[..., 0]
    transformed[..., 1:] = (standardized[..., 1:] - correlation * standardized[..., :-1]) / np.sqrt(1 - correlation ** 2)
    return transformed.reshape(len(values), -1)


def simplex(values):
    flat = values.reshape(-1, values.shape[-1])
    ordered = np.sort(flat, axis=1)[:, ::-1]
    levels = (np.cumsum(ordered, axis=1) - 1) / np.arange(1, flat.shape[1] + 1)
    active = np.sum(ordered > levels, axis=1) - 1
    threshold = levels[np.arange(len(flat)), active]
    return np.maximum(flat - threshold[:, None], 0).reshape(values.shape)


def fit_predict(train, targets, query, reference_sigma, correlation):
    features = transform(train, reference_sigma, correlation)
    observed = transform(query, reference_sigma, correlation)
    center = features.mean(axis=0)
    target_center = targets.mean(axis=0)
    left, singular, right = svd(features - center, full_matrices=False, check_finite=False)
    regularizer = 24 * len(train)
    coefficients = right.T @ ((singular / (singular ** 2 + regularizer))[:, None]
                              * (left.T @ (targets - target_center)))
    global_prediction = target_center + (observed - center) @ coefficients
    rank = min(12, len(singular))
    scale = np.maximum(singular[:rank] / np.sqrt(len(train)), 40)
    train_coords = (features - center) @ right[:rank].T / scale
    query_coords = (observed - center) @ right[:rank].T / scale
    predictions = []
    neighbors = min(120, len(train))
    for index, coordinate in enumerate(query_coords):
        distances = np.sum((train_coords - coordinate) ** 2, axis=1)
        selected = np.argpartition(distances, neighbors - 1)[:neighbors]
        bandwidth = max(np.median(distances[selected]), .1)
        weights = np.exp(-distances[selected] / bandwidth)
        weights /= weights.sum()
        local_center = weights @ features[selected]
        local_target = weights @ targets[selected]
        local_features = (features[selected] - local_center) * np.sqrt(weights[:, None])
        local_labels = (targets[selected] - local_target) * np.sqrt(weights[:, None])
        local_left, local_singular, local_right = svd(local_features, full_matrices=False, check_finite=False)
        local_coefficients = local_right.T @ ((local_singular / (local_singular ** 2 + 36))[:, None]
                                              * (local_left.T @ local_labels))
        local_prediction = local_target + (observed[index] - local_center) @ local_coefficients
        predictions.append(.25 * global_prediction[index] + .75 * local_prediction)
    return np.asarray(predictions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    public = public_directory()
    with np.load(public / "train_features.npz", allow_pickle=False) as archive:
        train = archive["observed"]
        reference_sigma = np.median(archive["sigma"], axis=0)
        correlation = float(archive["noise_correlation"])
    with np.load(public / "train_labels.npz", allow_pickle=False) as archive:
        target_shape = archive["spectral_mass"].shape[1:]
        targets = archive["spectral_mass"].reshape(len(train), -1)
    with np.load(arguments.input, allow_pickle=False) as archive:
        query = archive["observed"]
    prediction = fit_predict(train, targets, query, reference_sigma, correlation)
    prediction = simplex(prediction.reshape((len(query),) + target_shape))
    np.savez_compressed(arguments.output, spectral_mass=prediction)


if __name__ == "__main__":
    main()
