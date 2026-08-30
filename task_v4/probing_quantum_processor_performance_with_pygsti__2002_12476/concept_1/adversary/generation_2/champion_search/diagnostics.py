import hashlib
import itertools
import json
import os
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, ROOT, usability_compare, write_json

sys.path.insert(0, str(ROOT / "generations/generation_1/participant/workspace"))
from physics import fisher_features


def load_profile(path):
    with np.load(path, allow_pickle=False) as source:
        profiles = {key[len("champion_"):]: source[key].copy() for key in source.files if key.startswith("champion_")}
        families = source["families"].copy()
    return profiles, families


def main():
    benchmark = Benchmark()
    benchmark.freeze()
    summary = dict(private_provisional_only=True, held_out_main_600_read=False,
                   held_out_main_600_used_for_fitting=False, primary_objective="absolute 4x/5x usability caps")
    for name in ["hidden", "broad", "boundary", "confirmation"]:
        path = HERE / f"{name}_scores.json"
        scores = json.loads(path.read_text())["champion"]
        profile, families = load_profile(HERE / f"{name}_profiles.npz")
        scores["usability_comparison"] = usability_compare(profile, profile, families)
        scores["top_1_percent_triple_risk_share"] = float(np.sort(profile["loss_3"])[-max(1, int(np.ceil(len(families) * .01))):].sum() / profile["loss_3"].sum())
        summary[name] = scores
    broad, families = load_profile(HERE / "broad_profiles.npz")
    rng = np.random.default_rng(159330702)
    bootstrap = {}
    for count in [10, 100]:
        selections = [rng.choice(np.flatnonzero(families == family), (1000, count), replace=True) for family in np.unique(families)]
        indices = np.concatenate(selections, axis=1)
        bootstrap[str(6 * count)] = {}
        for order in [2, 3]:
            means = broad[f"loss_{order}"][indices].mean(axis=1)
            bootstrap[str(6 * count)][str(order)] = dict(mean=float(means.mean()), coefficient_of_variation=float(means.std() / means.mean()),
                quantiles={str(quantile): float(np.quantile(means, quantile)) for quantile in [.05, .5, .95, .99]},
                minimum=float(means.min()), maximum=float(means.max()))
    summary["stratified_empirical_bootstrap"] = dict(replicates=1000, seed=159330702, values=bootstrap,
        caveat="finite empirical resampling diagnostic, not a proof of population tail moments")
    with np.load(HERE / "boundary_features.npz", allow_pickle=False) as source:
        parameters = source["parameters"].copy()
        families = source["families"].copy()
        zero_index = int(np.flatnonzero(source["coherent_scales"] == 0)[0])
    point = parameters[zero_index]
    support = np.flatnonzero(benchmark.reference_counts)
    candidates = [benchmark.candidates[index] for index in support]
    removed = [461, 471, 476]
    keep = ~np.isin(support, removed)
    details = {}
    for step in [1e-5, 1e-6, 1e-7]:
        features = fisher_features(point, candidates, step=step)
        rows = features * np.sqrt(64 * benchmark.reference_counts[support])[:, None]
        remaining = rows[keep]
        singular_values = np.linalg.svd(remaining, compute_uv=False)
        information = remaining.T @ remaining
        risks = {}
        for ridge in [1e-8, 1e-10, 1e-12]:
            inverse = np.linalg.inv(information + np.eye(14) * ridge)
            risks[str(ridge)] = float(np.trace(inverse[:12, :12]))
        details[str(step)] = dict(remaining_singular_values=singular_values.tolist(),
            nonzero_Y_z_circuits=support[np.abs(features[:, 5]) > 1e-7].tolist(),
            remaining_Y_z_feature_norm=float(np.linalg.norm(features[keep, 5])), ridge_risks=risks)
    summary["ideal_limit_identifiability_audit"] = dict(parameters=point.tolist(), family=str(families[zero_index]),
        lost_circuits=removed, finite_difference_checks=details,
        interpretation="removal of the three short Y-z-sensitive probes produces an unidentifiable Y_z direction at zero coherent error; the remaining risk is controlled by the numerical ridge")
    write_json(HERE / "champion_diagnostics.json", summary)
    print(json.dumps(dict(hidden_triple=summary["hidden"]["loss_3"]["mean"], broad_triple=summary["broad"]["loss_3"]["mean"],
                          bootstrap=bootstrap, ideal_limit=details), indent=2))


if __name__ == "__main__":
    main()
