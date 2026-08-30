import collections
import math


def likelihood_interval(shots, errors, ratio):
    if not 0 <= errors <= shots or shots <= 0 or ratio <= 1:
        raise ValueError("invalid count likelihood")
    budget = math.log(ratio)
    if errors == 0:
        return 0.0, -math.expm1(-budget / shots)
    if errors == shots:
        return math.exp(-budget / shots), 1.0
    empirical = errors / shots

    def regret(probability):
        if probability <= 0 or probability >= 1:
            return math.inf
        return (errors * math.log(empirical / probability)
                + (shots - errors) * (math.log1p(-empirical) - math.log1p(-probability)))

    left, right = 0.0, empirical
    for iteration in range(90):
        middle = (left + right) / 2
        if regret(middle) > budget:
            left = middle
        else:
            right = middle
    lower = right
    left, right = empirical, 1.0
    for iteration in range(90):
        middle = (left + right) / 2
        if regret(middle) > budget:
            right = middle
        else:
            left = middle
    return lower, left


def row_error(probability, lower, upper):
    if probability < lower:
        return math.log10(lower) - math.log10(probability)
    if probability > upper:
        return math.log10(probability) - math.log10(upper)
    return 0.0


def score_predictions(predictions, labels, protocol):
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    diagnostics = []
    for row in labels:
        probability = predictions[row["query_id"]]
        if not math.isfinite(probability) or not protocol["probability_min"] <= probability <= protocol["probability_max"]:
            raise ValueError("invalid probability")
        lower, upper = likelihood_interval(row["num_shots"], row["num_shots"] - row["num_correct"], protocol["likelihood_ratio"])
        error = row_error(probability, lower, upper)
        if row["stress"] == "joint":
            diagnostics.append(error**2)
        else:
            key = "/".join([row["circuit_style"], row["decoder"], row["stress"]])
            cells[key][row["preserved_observable"]].append(error**2)
    results = {}
    for key, observables in sorted(cells.items()):
        if len(observables) != 2:
            raise ValueError("incomplete observable family")
        mean_square = sum(sum(values) / len(values) for values in observables.values()) / 2
        results[key] = {"rms_log10": math.sqrt(mean_square), "rows": sum(map(len, observables.values()))}
    if len(results) != 20 or sum(cell["rows"] for cell in results.values()) != protocol["scored_rows"]:
        raise ValueError("incomplete scoring families")
    if len(diagnostics) != protocol["diagnostic_rows"]:
        raise ValueError("incomplete diagnostics")
    worst = max(cell["rms_log10"] for cell in results.values())
    core = math.sqrt(sum(cell["rms_log10"]**2 for cell in results.values()) / len(results))
    return {"valid": True, "score": 10**(-worst), "core_score": 10**(-core),
            "worst_family_score": 10**(-worst),
            "success": worst <= protocol["worst_cell_rms_log10_max"],
            "worst_cell_rms_log10": worst, "cells": results,
            "joint_diagnostic_rms_log10": math.sqrt(sum(diagnostics) / len(diagnostics)),
            "scored_rows": protocol["scored_rows"], "diagnostic_rows": len(diagnostics)}
