from __future__ import annotations

import numpy as np

CORE = ("logical_accuracy", "history_balanced_accuracy")


def wilson_interval(successes, shots):
    probability = successes / shots
    quantile = 1.959963984540054
    denominator = 1 + quantile**2 / shots
    center = (probability + quantile**2 / (2 * shots)) / denominator
    radius = quantile * np.sqrt(probability * (1 - probability) / shots + quantile**2 / (4 * shots**2)) / denominator
    return [float(max(0, center - radius)), float(min(1, center + radius))]


def load_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def measure(case, truth, answer):
    shots, rounds, num_checks = case["readout"].shape
    num_qubits = case["checks"].shape[1]
    required = {
        "increments": (shots, rounds, num_qubits),
        "syndrome_history": (shots, rounds, num_checks),
    }
    for name, shape in required.items():
        if name not in answer:
            raise ValueError(f"Missing output array: {name}")
        array = answer[name]
        if array.shape != shape or array.dtype.kind not in "biu":
            raise ValueError(f"{name} must be a binary integer array of shape {shape}")
        if np.any((array != 0) & (array != 1)):
            raise ValueError(f"{name} contains nonbinary values")
    increments = answer["increments"].astype(np.uint8)
    reported = answer["syndrome_history"].astype(np.uint8)
    cumulative = np.cumsum(increments, axis=1, dtype=np.int32) % 2
    reconstructed = cumulative @ case["checks"].T % 2
    history_consistent = np.all(reported == reconstructed, axis=(1, 2))
    boundary_consistent = np.all(reconstructed[:, -1] == case["terminal_syndrome"], axis=1)
    meta_consistent = np.all(reported @ case["metachecks"].T % 2 == 0, axis=(1, 2))
    valid = history_consistent & boundary_consistent & meta_consistent
    residual = (cumulative[:, -1] + truth["final_error"]) % 2
    logical_success = valid & np.all(residual @ truth["logical_checks"].T % 2 == 0, axis=1)
    latent = truth["syndrome_history"][:, :-1]
    correct = (reported[:, :-1] == latent) & valid[:, None, None]
    positive = latent == 1
    negative = ~positive
    if not np.any(positive) or not np.any(negative):
        raise ValueError("Degenerate truth corpus for balanced history scoring")
    balanced = 0.5 * (np.mean(correct[positive]) + np.mean(correct[negative]))
    return {
        "shots": shots,
        "logical_successes": int(np.sum(logical_success)),
        "logical_accuracy": float(np.mean(logical_success)),
        "logical_wilson95": wilson_interval(int(np.sum(logical_success)), shots),
        "logical_error_rate": float(1 - np.mean(logical_success)),
        "history_balanced_accuracy": float(balanced),
        "history_bit_accuracy": float(np.mean(correct)),
        "valid_fraction": float(np.mean(valid)),
        "history_consistency": float(np.mean(history_consistent)),
        "terminal_consistency": float(np.mean(boundary_consistent)),
        "meta_consistency": float(np.mean(meta_consistent)),
    }


def failure_metrics(shots):
    return {
        "shots": shots,
        "logical_successes": 0,
        "logical_accuracy": 0.0,
        "logical_wilson95": wilson_interval(0, shots),
        "logical_error_rate": 1.0,
        "history_balanced_accuracy": 0.0,
        "history_bit_accuracy": 0.0,
        "valid_fraction": 0.0,
        "history_consistency": 0.0,
        "terminal_consistency": 0.0,
        "meta_consistency": 0.0,
    }


def summarize(results, anchors):
    families = {}
    for family, family_anchors in anchors.items():
        cases = [result for result in results if result["family"] == family]
        raw = {metric: float(np.mean([case["metrics"][metric] for case in cases])) for metric in CORE}
        core = {}
        for metric in CORE:
            weak = family_anchors[metric]["weak"]
            reference = family_anchors[metric]["reference"]
            if reference <= weak:
                raise ValueError(f"No reference headroom: {family}/{metric}")
            core[metric] = (raw[metric] - weak) / (reference - weak)
        families[family] = {
            "raw": raw,
            "normalized_core": core,
            "mean_core": float(np.mean(list(core.values()))),
            "anchors": family_anchors,
            "runtime_seconds": float(sum(case.get("runtime_seconds", 0.0) for case in cases)),
            "shots": sum(case["metrics"]["shots"] for case in cases),
        }
    return {
        "mean_core": float(np.mean([family["mean_core"] for family in families.values()])),
        "worst_family": min(family["mean_core"] for family in families.values()),
        "per_family": families,
    }
