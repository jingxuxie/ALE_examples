"""Label-only numerical scoring; no model-building dependency."""

import math

import numpy as np


FAMILIES = ("cartesian_wsvec", "nearest_atom", "cell_gauge")
WEIGHTS = {"pos": 0.20, "h1": 0.35, "h2": 0.35, "bands": 0.10}


def numerical_error(actual, expected, absolute=False):
    actual = np.asarray(actual)
    expected = np.asarray(expected)
    if actual.shape != expected.shape:
        raise ValueError(f"shape {actual.shape}, expected {expected.shape}")
    if actual.dtype.kind not in "fciub" or not np.all(np.isfinite(actual)):
        raise ValueError("non-numeric or non-finite output")
    difference = np.abs(actual - expected)
    scale = 1.0 if absolute else max(float(np.sqrt(np.mean(np.abs(expected) ** 2))), 1e-12)
    normalized_rms = float(np.sqrt(np.mean(difference ** 2)) / scale)
    if not math.isfinite(normalized_rms):
        raise ValueError("numerical overflow")
    return {"normalized_rms": normalized_rms, "max_absolute": float(np.max(difference))}


def track_metrics(actual, expected, prefix):
    metrics = {}
    weighted_error = 0.0
    for suffix, weight in WEIGHTS.items():
        key = f"{prefix}_{suffix}"
        metrics[key] = numerical_error(actual[key], expected[key], absolute=suffix == "pos")
        weighted_error += weight * metrics[key]["normalized_rms"]
    if prefix == "map":
        metrics["map_uc"] = numerical_error(actual["map_uc"], expected["map_uc"])
        weighted_error = 0.95 * weighted_error + 0.05 * metrics["map_uc"]["normalized_rms"]
    return weighted_error, metrics


def score(error, weak_error):
    return 1.0 / (1.0 + 9.0 * error / max(weak_error, 1e-12))


def aggregate(per_case):
    family_scores = {}
    for family in FAMILIES:
        values = [case["families"][family]["score"] for case in per_case if family in case["families"]]
        family_scores[family] = sum(values) / len(values) if values else 0.0
    values = list(family_scores.values())
    core = math.prod(values) ** (1.0 / len(values))
    return {"core_score": core, "worst_family_score": min(values), "family_scores": family_scores}
