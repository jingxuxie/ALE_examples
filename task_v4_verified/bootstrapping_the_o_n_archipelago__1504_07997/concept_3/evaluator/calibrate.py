"""Privileged LOCAL Fisher design portfolio; not an executable reference policy."""

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "participant" / "input"))

from baseline_impl import fixed_design, predict
from hidden.generator import suite
from model import BUDGET, FAMILIES, SCALES, noise_std
from scoring import aggregate


PRIOR_STD = np.array([0.2, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3], dtype=float)


def gradients(instance, design):
    times = np.array([item[0] for item in design])
    probes = np.array([item[1] for item in design])
    parameters = [instance.delta0, math.log(instance.gap), math.log(instance.a0),
                  instance.theta0, math.log(instance.a1), instance.theta1]
    low = predict(parameters, times, probes, True)[1]
    matrix_entries = np.column_stack([probes[:, 0] ** 2, 2 * probes[:, 0] * probes[:, 1], probes[:, 1] ** 2])
    tail3 = matrix_entries * np.exp(-3 * times[:, None])
    tail5 = matrix_entries * np.exp(-5 * times[:, None])
    return np.column_stack([low, tail3, tail5]) * PRIOR_STD / noise_std(times)[:, None]


def covariance(derivatives):
    information = np.eye(len(PRIOR_STD)) + derivatives.T @ derivatives
    return np.linalg.solve(information, np.eye(len(PRIOR_STD)))


def design_greedy(instance, candidates):
    derivatives = gradients(instance, candidates)
    current = np.eye(len(PRIOR_STD))
    weights = (PRIOR_STD[:4] / SCALES) ** 2
    selected = []
    for step in range(BUDGET):
        projected = derivatives @ current
        denominator = 1 + np.sum(projected * derivatives, axis=1)
        benefit = np.sum(projected[:, :4] ** 2 * weights, axis=1) / denominator
        chosen = int(np.argmax(benefit))
        update = projected[chosen]
        current -= np.outer(update, update) / denominator[chosen]
        current = (current + current.T) / 2
        selected.append(candidates[chosen])
    return selected, covariance(gradients(instance, selected))


def predicted_loss(matrix):
    standard = np.sqrt(np.maximum(matrix.diagonal()[:4], 0)) * PRIOR_STD[:4] / SCALES
    quantile = norm.ppf(0.95)
    expected_interval = (2 * quantile + 20 * (2 * norm.pdf(quantile) - 0.1 * quantile)) / 4
    coefficient = 0.7 * math.sqrt(2 / math.pi) + 0.3 * expected_interval
    return float(coefficient * standard.mean())


def main():
    candidates = [
        (float(time), [math.cos(angle), math.sin(angle)])
        for time in np.linspace(1.2, 6.0, 25)
        for angle in np.linspace(0, math.pi, 24, endpoint=False)
    ]
    late = [
        (time, [math.cos(angle), math.sin(angle)])
        for time in (2.5, 3.1, 3.7, 4.3, 5.0, 5.8)
        for angle in (0, math.pi / 4, math.pi / 2, 3 * math.pi / 4)
        for repeat in range(3)
    ]
    records = []
    for record in suite("calibration-v1", 4):
        instance = record["instance"]
        chosen, designed = design_greedy(instance, candidates)
        records.append({
            "id": record["id"], "family": instance.family,
            "fixed": predicted_loss(covariance(gradients(instance, fixed_design()))),
            "late_fixed": predicted_loss(covariance(gradients(instance, late))),
            "privileged_greedy": predicted_loss(designed),
            "fraction_t_below_3": sum(item[0] < 3 for item in chosen) / BUDGET,
            "fraction_t_above_4": sum(item[0] > 4 for item in chosen) / BUDGET,
        })
    families = {}
    for family in FAMILIES:
        selected = [record for record in records if record["family"] == family]
        families[family] = {
            key: float(np.mean([record[key] for record in selected]))
            for key in ("fixed", "late_fixed", "privileged_greedy")
        }
    robust = {
        key: 0.35 * np.mean([family[key] for family in families.values()])
        + 0.65 * max(family[key] for family in families.values())
        for key in ("fixed", "late_fixed", "privileged_greedy")
    }
    result = {
        "kind": "privileged_local_information_only", "operational_success_claimed": False,
        "assumptions": [
            "The design knows the true low-state parameters; no such knowledge is given to entrants.",
            "Unknown tail is locally approximated by free symmetric matrices at exponents 3 and 5.",
            "A broad diagonal regularizing prior stabilizes local information inversion.",
            "No finite-sample fit, continuum misspecification, or posterior multimodality is certified.",
            "This is evidence of allocation sensitivity, not an information-theoretic or feasible-policy bound.",
        ],
        "calls_each": BUDGET, "families": families,
        "predicted_robust_losses": robust, "cases": records,
    }
    (BASE / "attempts" / "privileged_design_report.json").write_text(json.dumps(result, indent=2) + "\n")
    report_path = BASE / "attempts" / "baseline_report.json"
    baseline = json.loads(report_path.read_text())
    raw_path = BASE / "attempts" / "baseline_calibration_raw.json"
    if not raw_path.exists():
        raw_path.write_text(json.dumps(baseline, indent=2) + "\n")
    target_bytes = (BASE / "participant" / "input" / "target.json").read_bytes()
    target = json.loads(target_bytes)
    baseline.update(aggregate(baseline["cases"], target, False))
    baseline["target"] = target
    baseline["target_sha256"] = hashlib.sha256(target_bytes).hexdigest()
    baseline["note"] = "Existing pre-fresh measurements rescored against frozen target; raw initial report preserved."
    report_path.write_text(json.dumps(baseline, indent=2) + "\n")
    print(json.dumps({"predicted_robust_losses": robust, "families": families}, indent=2))


if __name__ == "__main__":
    main()
