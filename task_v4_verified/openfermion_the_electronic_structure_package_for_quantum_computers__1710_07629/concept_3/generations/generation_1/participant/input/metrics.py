"""Trusted metric implementation; never imports participant or submitted code."""

import json
import math

import numpy as np


def parse_predictions(text, count):
    def reject_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    payload = json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "predictions"}:
        raise ValueError("expected exactly schema_version and predictions")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    predictions = payload["predictions"]
    if not isinstance(predictions, list) or len(predictions) != count:
        raise ValueError("prediction row count mismatch")
    for row in predictions:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("each prediction must be [charge_gap, spin_gap]")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("predictions must be finite real JSON numbers, not booleans")
            if abs(value) > 1e100:
                raise ValueError("numerically unsafe prediction magnitude")
    return np.asarray(predictions, dtype=np.float64)


def score_predictions(predictions, labels, families, settings):
    errors = predictions - labels
    rmse = np.sqrt(np.mean(errors ** 2, axis=0))
    ratio = max(rmse[0] / settings["charge_rmse_limit"],
                rmse[1] / settings["spin_rmse_limit"])
    family_report = {}
    worst_ratio = 0.0
    names = ("dimerized_ring", "open_ladder", "triangular_ladder", "periodic_ladder")
    for family, name in enumerate(names):
        selected = errors[families == family]
        if not len(selected):
            raise ValueError("all four families are required for scoring")
        family_rmse = np.sqrt(np.mean(selected ** 2, axis=0))
        family_report[name] = {"count": len(selected), "charge_rmse": float(family_rmse[0]),
                               "spin_rmse": float(family_rmse[1])}
        worst_ratio = max(worst_ratio, family_rmse[0] / settings["family_charge_rmse_limit"],
                          family_rmse[1] / settings["family_spin_rmse_limit"])
    return {"core_score": float(1.0 / (1.0 + ratio)),
            "worst_family_score": float(1.0 / (1.0 + worst_ratio)),
            "charge_rmse": float(rmse[0]), "spin_rmse": float(rmse[1]),
            "family_scores": family_report,
            "accuracy_passed": bool(ratio <= 1.0 and worst_ratio <= 1.0)}
