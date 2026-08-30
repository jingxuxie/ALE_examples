import math

from common import ROOT

import numpy as np
from evaluate import paired_report


def wilson(failures, shots):
    if not shots:
        return None
    quantile = 1.959963984540054
    rate = failures / shots
    denominator = 1 + quantile ** 2 / shots
    center = (rate + quantile ** 2 / (2 * shots)) / denominator
    radius = quantile * math.sqrt(rate * (1 - rate) / shots + quantile ** 2 / (4 * shots ** 2)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def summarize_pair(baseline_wrong, candidate_wrong):
    baseline_wrong = np.asarray(baseline_wrong, dtype=bool)
    candidate_wrong = np.asarray(candidate_wrong, dtype=bool)
    shots = len(candidate_wrong)
    if shots >= 2:
        report = paired_report(baseline_wrong, candidate_wrong)
    else:
        report = dict(shots=shots, baseline_failures=int(baseline_wrong.sum()), candidate_failures=int(candidate_wrong.sum()),
                      error_reduction=None, paired_absolute_ci95=None, paired_relative_ci95=None,
                      corrected=int((baseline_wrong & ~candidate_wrong).sum()), spoiled=int((~baseline_wrong & candidate_wrong).sum()))
    report["candidate_rate_ci95"] = wilson(int(candidate_wrong.sum()), shots)
    report["baseline_rate_ci95"] = wilson(int(baseline_wrong.sum()), shots)
    report["few_residuals_warning"] = int(candidate_wrong.sum()) < 20
    return report


def component_features(active_mechanisms, supports, coordinates):
    parents = {}
    members = {}

    def root(detector):
        while parents[detector] != detector:
            parents[detector] = parents[parents[detector]]
            detector = parents[detector]
        return detector

    for mechanism in active_mechanisms:
        detectors = supports[mechanism]
        for detector in detectors:
            detector = int(detector)
            parents.setdefault(detector, detector)
        if len(detectors):
            first = root(int(detectors[0]))
            for detector in detectors[1:]:
                other = root(int(detector))
                parents[other] = first
    for mechanism in active_mechanisms:
        if len(supports[mechanism]):
            representative = root(int(supports[mechanism][0]))
            members[representative] = members.get(representative, 0) + 1
    time_ranges = {}
    for detector in parents:
        representative = root(detector)
        time = int(coordinates[detector, 2])
        bounds = time_ranges.setdefault(representative, [time, time])
        bounds[0] = min(bounds[0], time)
        bounds[1] = max(bounds[1], time)
    return len(members), max(members.values(), default=0), max((upper - lower for lower, upper in time_ranges.values()), default=0)


def extract_features(model, syndromes, faults):
    supports = [np.flatnonzero(model["detector_matrix"][:, mechanism]) for mechanism in range(model["num_mechanisms"])]
    features = dict(fault_count=faults.sum(axis=1).astype(np.int64), syndrome_weight=syndromes.sum(axis=1).astype(np.int64))
    for kind in sorted(set(model["mechanism_kind"])):
        features["count_" + kind] = faults[:, model["mechanism_kind"] == kind].sum(axis=1).astype(np.int64)
    component_counts, largest_components, time_extents = [], [], []
    for fault_row in faults:
        count, largest, extent = component_features(np.flatnonzero(fault_row), supports, model["detector_coordinates"])
        component_counts.append(count)
        largest_components.append(largest)
        time_extents.append(extent)
    features["component_count"] = np.asarray(component_counts)
    features["largest_fault_component"] = np.asarray(largest_components)
    features["largest_component_time_extent"] = np.asarray(time_extents)
    incidence_mass = faults.astype(np.int64) @ np.asarray([len(support) for support in supports], dtype=np.int64)
    features["syndrome_cancellation_fraction"] = 1 - features["syndrome_weight"] / np.maximum(1, incidence_mass)
    probabilities = model["probabilities"]
    features["fault_surprisal"] = -float(np.log1p(-probabilities).sum()) + faults @ np.log((1 - probabilities) / probabilities)
    return features


def residual_report(model, syndromes, labels, baseline, predictions, features, minimum_exposure=16):
    baseline_wrong = np.any(baseline != labels, axis=1)
    candidate_wrong = np.any(predictions != labels, axis=1)
    zeros = np.zeros(len(labels), dtype=np.int64)
    pairs = features.get("count_XX", zeros) + features.get("count_ZZ", zeros)
    temporal = (features.get("count_readout", zeros) > 0) & (features.get("count_YY_time", zeros) > 0)
    masks = {
        "readout_and_temporal_burst": temporal,
        "spatial_pair_and_temporal_burst": (pairs > 0) & (features.get("count_YY_time", zeros) > 0),
        "multiple_spatial_pair_events": pairs >= 2,
        "extended_true_fault_component": features["largest_fault_component"] >= model["distance"],
        "large_syndrome_cancellation": features["syndrome_cancellation_fraction"] >= 0.5,
        "small_true_fault_components": features["largest_fault_component"] < max(2, model["distance"] // 2),
    }
    strata = {name: summarize_pair(baseline_wrong[mask], candidate_wrong[mask]) for name, mask in masks.items() if mask.any()}
    feature_bins = {}
    for name, values in features.items():
        edges = np.unique(np.quantile(values, [0.0, 0.25, 0.5, 0.75, 1.0]))
        bins = []
        for index in range(len(edges) - 1):
            mask = (values >= edges[index]) & ((values <= edges[index + 1]) if index == len(edges) - 2 else (values < edges[index + 1]))
            if mask.any():
                bins.append(dict(lower=float(edges[index]), upper=float(edges[index + 1]),
                                 **summarize_pair(baseline_wrong[mask], candidate_wrong[mask])))
        feature_bins[name] = bins
    masks_logical = (np.asarray(predictions ^ labels, dtype=np.int64) * np.asarray([1, 2, 4, 8])).sum(axis=1)
    logical_patterns = {str(mask): int((masks_logical == mask).sum()) for mask in range(1, 16)}
    exposures = syndromes.sum(axis=0).astype(np.int64)
    failure_exposures = syndromes[candidate_wrong].sum(axis=0).astype(np.int64)
    overall_rate = float(candidate_wrong.mean())
    hotspots = []
    for detector in np.flatnonzero(exposures >= minimum_exposure):
        total = int(exposures[detector])
        failures = int(failure_exposures[detector])
        conditional_rate = failures / total
        hotspots.append(dict(detector=int(detector), coordinates=model["detector_coordinates"][detector].tolist(),
                             exposures=total, failure_exposures=failures, conditional_failure_rate=conditional_rate,
                             conditional_ci95=wilson(failures, total), descriptive_lift=conditional_rate / overall_rate if overall_rate else None,
                             ranking_statistic=(conditional_rate - overall_rate) * math.sqrt(total)))
    hotspots.sort(key=lambda entry: (-entry["ranking_statistic"], -entry["failure_exposures"], entry["detector"]))
    return dict(summary=summarize_pair(baseline_wrong, candidate_wrong), overlapping_residual_strata=strata,
                feature_quantile_bins=feature_bins, logical_confusion_masks=logical_patterns, detector_hotspots=hotspots[:24],
                joint_css_failures=int((((masks_logical & 3) != 0) & ((masks_logical & 12) != 0)).sum()),
                caveat="Descriptive associations with sampled fault geometry, not proven causal error explanations or posterior gaps. Hotspots/strata are exploratory and multiple comparisons are uncorrected.")
