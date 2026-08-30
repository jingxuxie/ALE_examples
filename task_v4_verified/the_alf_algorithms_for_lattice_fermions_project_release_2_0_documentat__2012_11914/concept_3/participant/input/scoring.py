"""Public numerical scoring contract; never executes a submission."""

import numpy as np

from physics import FAMILY_NAMES, QUANTILE_LEVELS, observables, wasserstein


def validate_prediction(prediction, inputs):
    expected = {"sample_id", "spectral_mass", "low_mass_quantiles"}
    if set(prediction) != expected:
        raise ValueError("output must contain exactly sample_id, spectral_mass, low_mass_quantiles")
    count = len(inputs["sample_id"])
    bins = len(inputs["omega_edges"]) - 1
    sample_id = np.asarray(prediction["sample_id"])
    if sample_id.dtype != np.dtype("uint64") or not np.array_equal(sample_id, inputs["sample_id"]):
        raise ValueError("sample_id must exactly preserve input uint64 IDs and row order")
    mass = np.asarray(prediction["spectral_mass"])
    quantiles = np.asarray(prediction["low_mass_quantiles"])
    for name, array, shape in (
        ("spectral_mass", mass, (count, bins)),
        ("low_mass_quantiles", quantiles, (count, 3)),
    ):
        if array.dtype.kind != "f" or array.shape != shape:
            raise ValueError(f"{name} must be a real floating array with shape {shape}")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{name} must be finite")
        if np.any(array < 0.0) or np.any(array > 1.0):
            raise ValueError(f"{name} entries must lie in [0,1]")
    if not np.allclose(mass.sum(axis=1), 1.0, rtol=0.0, atol=1e-6):
        raise ValueError("spectral_mass rows must sum to one within 1e-6")
    if np.any(np.diff(quantiles, axis=1) < 0.0):
        raise ValueError("low_mass_quantiles must be nondecreasing")


def score_prediction(prediction, inputs, labels):
    validate_prediction(prediction, inputs)
    if not np.array_equal(inputs["sample_id"], labels["sample_id"]):
        raise ValueError("trusted label alignment failure")
    predicted_mass = prediction["spectral_mass"].astype(np.float64)
    predicted_mass /= predicted_mass.sum(axis=1, keepdims=True)
    truth = labels["spectral_mass"]
    predicted = observables(predicted_mass, inputs["omega_edges"])
    actual = observables(truth, inputs["omega_edges"])
    normalized_w1 = wasserstein(predicted_mass, truth, inputs["omega_edges"]) / 16.0
    low_error = np.abs(predicted["low_mass"] - actual["low_mass"])
    band_error = np.abs(predicted["band_weights"] - actual["band_weights"]).sum(axis=1) / 2.0
    gap_error = np.abs(predicted["gap10"] - actual["gap10"])
    residual = actual["low_mass"][:, None] - prediction["low_mass_quantiles"]
    pinball = np.maximum(QUANTILE_LEVELS * residual, (QUANTILE_LEVELS - 1.0) * residual).mean(axis=1)
    loss = (
        0.45 * normalized_w1 / 0.02
        + 0.20 * low_error / 0.06
        + 0.15 * band_error / 0.10
        + 0.10 * gap_error / 0.40
        + 0.10 * pinball / 0.02
    )
    family_scores = {}
    family_metrics = {}
    for family_index, family_name in enumerate(FAMILY_NAMES):
        selected = labels["family_id"] == family_index
        if not np.any(selected):
            continue
        family_scores[family_name] = float(100.0 * np.exp(-np.mean(loss[selected])))
        family_metrics[family_name] = {
            "count": int(selected.sum()),
            "normalized_wasserstein": float(np.mean(normalized_w1[selected])),
            "low_mass_mae": float(np.mean(low_error[selected])),
            "band_total_variation": float(np.mean(band_error[selected])),
            "gap10_mae": float(np.mean(gap_error[selected])),
            "quantile_pinball": float(np.mean(pinball[selected])),
        }
    quantiles = prediction["low_mass_quantiles"]
    return {
        "core_score": float(100.0 * np.exp(-np.mean(loss))),
        "worst_family_score": min(family_scores.values()),
        "family_scores": family_scores,
        "metrics": {
            "normalized_wasserstein": float(np.mean(normalized_w1)),
            "low_mass_mae": float(np.mean(low_error)),
            "band_total_variation": float(np.mean(band_error)),
            "gap10_mae": float(np.mean(gap_error)),
            "quantile_pinball": float(np.mean(pinball)),
            "low_mass_80pct_coverage": float(np.mean((actual["low_mass"] >= quantiles[:, 0]) & (actual["low_mass"] <= quantiles[:, 2]))),
            "low_mass_80pct_width": float(np.mean(quantiles[:, 2] - quantiles[:, 0])),
        },
        "family_metrics": family_metrics,
    }
