"""Finite global ambiguity search; neither an oracle solver nor a proof."""

import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "champions" / "portfolio"))
from inference import dictionary, infer, generator
from evaluate import score, target_configuration


def unordered_distance(first, second, bands):
    return min(float(np.sqrt(np.mean(((first[:bands] - second[list(order)]) / generator.MASS_SCALES) ** 2)))
               for order in itertools.permutations(range(bands)))


def sheet_features(parameters, family):
    energy, width, coherence, weight = generator.components(parameters, family)
    shifted = generator.OMEGA[:, None] + width
    denominator = shifted ** 2 + energy ** 2
    diagonal = generator.OMEGA[:, None] * shifted / denominator
    anomalous = generator.OMEGA[:, None] * (coherence * energy) / denominator
    bands = 3 if family == 3 else 2
    count = len(energy) // bands
    result = []
    for band in range(bands):
        section = slice(band * count, (band + 1) * count)
        measure = weight[0, section] / weight[0, section].sum()
        result.append(np.stack((diagonal[:, section] @ measure, anomalous[:, section] @ measure)))
    return np.asarray(result)


def mix(curves, parameters):
    bands = len(curves)
    if bands == 2:
        first = .25 + .5 * parameters[0]
        weights = np.array([first, 1 - first])
    else:
        first = .18 + .3 * parameters[0]
        second = (1 - first) * (.3 + .4 * parameters[1])
        weights = np.array([first, second, 1 - first - second])
    probes = generator.PROBE[:, :bands] * weights
    probes /= probes.sum(axis=1, keepdims=True)
    return np.einsum("pb,bcn->pcn", probes, curves)


def main():
    hidden = ROOT / "evaluator" / "hidden"
    configuration, target_hash = target_configuration()
    with np.load(hidden / "audit_features.npz", allow_pickle=False) as archive:
        observed, sigma, counts = archive["observed"], archive["sigma"], archive["sheet_count"]
    with np.load(hidden / "audit_latent.npz", allow_pickle=False) as archive:
        truth_parameters, truth_families, truth_clean = archive["parameters"], archive["family"], archive["clean"]
    with np.load(hidden / "audit_labels.npz", allow_pickle=False) as archive:
        labels = archive["spectral_mass"]
    permutations = []
    for index, family in enumerate(truth_families):
        bands = int(counts[index])
        curves = sheet_features(truth_parameters[index], int(family))
        minimum = np.inf
        closest = None
        for order in itertools.permutations(range(bands)):
            if order == tuple(range(bands)):
                continue
            permuted = curves[list(order)]
            def residual(weights):
                return generator.whiten(mix(permuted, weights) - truth_clean[index], sigma[index]).ravel()
            for initial in itertools.product((.15, .5, .85), repeat=bands - 1):
                fit = least_squares(residual, initial, bounds=(0, 1), max_nfev=100, ftol=1.e-10, xtol=1.e-10, gtol=1.e-9)
                separation = float(np.linalg.norm(residual(fit.x)))
                if separation < minimum:
                    minimum = separation
                    target = labels[index].copy()
                    target[:bands] = target[list(order)]
                    closest = dict(order=list(order), fitted_mixture_coordinates=fit.x.tolist(),
                                   ordered_target_distance=float(np.sqrt(np.mean(((labels[index, :bands] - target[:bands]) / generator.MASS_SCALES) ** 2))),
                                   unordered_target_distance=unordered_distance(labels[index], target, bands))
        permutations.append(dict(case=index, whitened_feature_separation=minimum, closest=closest))
        print("permutation", index, minimum, flush=True)
    report = dict(target_sha256=target_hash, permutation_and_weight_search=permutations,
                  permutation_scope="All nonidentity whole-sheet permutations, 3 or 9 mixture starts per permutation; original sheet curves held fixed, mixture reoptimized in its full disclosed domain. Allowing arbitrary permutation of curves is conservative: some permutations lie outside the gap/phase domains.",
                  truth_role="Latents used only for explicit alias diagnostics, not to initialize or score the blind fit below.",
                  global_scope="Independent public-seed model bank; three starts per compatible family; no truth initialization; finite search, not uniqueness proof.",
                  blind_cases=[], limitations=["Unrestricted three-sheet unmixing from two probes has a functional nullspace; attainability relies on the disclosed finite spectral family.",
                                               "Absence of a collision in a finite search is not a global certificate.",
                                               "A near-collision is a risk diagnostic, not by itself an aggregate Bayes-risk lower bound."])
    path = hidden / "global_identifiability.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    bank = dictionary()
    predictions, all_parameters, all_families, all_case_indices = [], [], [], []
    started = time.process_time()
    for index in range(len(observed)):
        prediction, diagnostic, fits = infer(observed[index], sigma[index], bank, starts=3, sheet_count=int(counts[index]))
        predictions.append(prediction)
        compatible = [fit for fit in fits if fit["chi_square"] <= fits[0]["chi_square"] + 9]
        features = [generator.clean_observations(fit["parameters"], fit["family"]) for fit in compatible]
        pairs = []
        for first, second in itertools.combinations(range(len(compatible)), 2):
            feature_distance = float(np.linalg.norm(generator.whiten(features[first] - features[second], sigma[index])))
            target_distance = unordered_distance(compatible[first]["mass"], compatible[second]["mass"], int(counts[index]))
            pairs.append(dict(first_family=compatible[first]["family"], second_family=compatible[second]["family"],
                              whitened_feature_distance=feature_distance, unordered_target_distance=target_distance,
                              collision_warning=feature_distance <= 2 and target_distance > 2))
        for fit in fits:
            all_parameters.append(fit["parameters"])
            all_families.append(fit["family"])
            all_case_indices.append(index)
        report["blind_cases"].append(dict(case=index, diagnostic=diagnostic, compatible_pairs=pairs))
        report["blind_cpu_seconds"] = time.process_time() - started
        report["blind_score"] = score(np.asarray(predictions), labels[:len(predictions)], truth_families[:len(predictions)], configuration)
        report["completed_cases"] = len(predictions)
        report["near_collision_count"] = sum(pair["collision_warning"] for case in report["blind_cases"] for pair in case["compatible_pairs"])
        path.write_text(json.dumps(report, indent=2) + "\n")
        np.savez_compressed(hidden / "global_fit_models.npz", parameters=np.asarray(all_parameters), family=np.asarray(all_families), case=np.asarray(all_case_indices))
        np.savez_compressed(hidden / "global_blind_prediction.npz", spectral_mass=np.asarray(predictions))
        print("blind", index, report["blind_score"]["core"], report["near_collision_count"], flush=True)


if __name__ == "__main__":
    main()
