import argparse
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, ROOT, compare, describe, profile, root_clusters, usability_compare, write_json

sys.path.insert(0, str(ROOT / "generations/generation_1/participant/workspace"))
from physics import FAMILIES, fisher_features, sample_parameters

OLD = ROOT / "adversary/portfolio/resilience_champion_1"


def prepare(name, required, benchmark):
    path = HERE / f"{name}_features.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as source:
            parameters, families = source["parameters"].copy(), source["families"].copy()
            union, features = source["candidate_union"].copy(), source["features"].copy()
            scale_values = source["coherent_scales"].copy() if "coherent_scales" in source.files else np.ones(len(families))
    elif name == "broad":
        with np.load(OLD / "broad_features.npz", allow_pickle=False) as source:
            parameters, families = source["parameters"].copy(), source["families"].copy()
            union, features = source["candidate_union"].copy(), source["features"].copy()
        scale_values = np.ones(len(families))
    else:
        rng = np.random.default_rng(627018399 if name == "confirmation" else 9927613)
        parameters, families, scale_values = [], [], []
        for family in FAMILIES:
            for iteration in range(100 if name == "confirmation" else 12):
                base = sample_parameters(rng, family)
                for scale in ([1.] if name == "confirmation" else [1., 0.3, 0.1, 0.03, 0.01, 0.]):
                    point = base.copy()
                    point[:9] *= scale
                    parameters.append(point)
                    families.append(family)
                    scale_values.append(scale)
        parameters, families, scale_values = np.array(parameters), np.array(families), np.array(scale_values)
        union = np.empty(0, dtype=int)
        features = np.empty((len(parameters), 0, 14))
    expanded_union = np.union1d(union, required)
    expanded = np.empty((len(parameters), len(expanded_union), 14))
    expanded[:, np.searchsorted(expanded_union, union)] = features
    missing = np.setdiff1d(expanded_union, union)
    positions = np.searchsorted(expanded_union, missing)
    candidates = [benchmark.candidates[index] for index in missing]
    for index, point in enumerate(parameters):
        if len(missing):
            expanded[index, positions] = fisher_features(point, candidates)
        if (index + 1) % 300 == 0:
            print(json.dumps(dict(event="features", dataset=name, complete=index + 1, total=len(parameters), missing=len(missing))), flush=True)
    np.savez_compressed(path, features=expanded, parameters=parameters, families=families,
                        candidate_union=expanded_union, coherent_scales=scale_values)
    return expanded, parameters, families, expanded_union, scale_values


def audit_dataset(name, features, parameters, families, union, scales, designs, benchmark, direct):
    started = time.monotonic()
    profiles = {label: profile(features, counts[union], direct=direct) for label, counts in designs.items()}
    report, roots = {}, {}
    arrays = dict(parameters=parameters, families=families, candidate_union=union, coherent_scales=scales)
    for label, counts in designs.items():
        result = profiles[label]
        report[label] = describe(result, families)
        report[label]["triple_comparison"] = compare(result, profiles["champion"], families)
        report[label]["usability_comparison"] = usability_compare(result, profiles["champion"], families)
        report[label]["every_deletion_directly_inverted"] = direct
        if direct:
            fast = profile(features, counts[union], direct=False)
            report[label]["rank_update_max_relative_error"] = {str(order): float(np.max(np.abs(fast[f"loss_{order}"] / result[f"loss_{order}"] - 1))) for order in [2, 3]}
        roots[label] = {str(order): root_clusters(features, counts[union], result, families, parameters, union, benchmark, order) for order in [2, 3]}
        for key, value in result.items():
            arrays[label + "_" + key] = value
        if name.endswith("boundary"):
            report[label]["coherent_attenuation"] = {str(scale): describe({key: value[scales == scale] for key, value in result.items() if key != "support"}, families[scales == scale]) for scale in np.unique(scales)}
        print(json.dumps(dict(event="audit", dataset=name, design=label, intact=report[label]["intact_mean"],
                              pair_mean=report[label]["loss_2"]["mean"], triple_mean=report[label]["loss_3"]["mean"],
                              maximum_triple=report[label]["loss_3"]["maximum"],
                              triple_to_pair=report[label]["triple_to_pair_mean_ratio"],
                              comparison=report[label]["triple_comparison"])), flush=True)
    write_json(HERE / f"{name}_scores.json", report)
    write_json(HERE / f"{name}_roots.json", roots)
    np.savez_compressed(HERE / f"{name}_profiles.npz", **arrays)
    print(json.dumps(dict(event="audit_finished", dataset=name, seconds=time.monotonic() - started)), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["hidden", "broad", "boundary", "confirmation"])
    parser.add_argument("--submission")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    benchmark = Benchmark()
    benchmark.freeze()
    designs = {"champion": benchmark.reference_counts}
    if args.submission:
        designs["candidate"] = np.array(json.loads((HERE / args.submission).read_text())["batches"])
        benchmark.validate(designs["candidate"])
    required = np.unique(np.concatenate([np.flatnonzero(counts) for counts in designs.values()]))
    results = {}
    for name in args.datasets:
        if name == "hidden":
            features, parameters, families, union, scales = benchmark.features, benchmark.parameters, benchmark.families, np.arange(840), np.ones(len(benchmark.families))
        else:
            features, parameters, families, union, scales = prepare(name, required, benchmark)
        if not args.prepare_only:
            results[name] = audit_dataset(args.prefix + name, features, parameters, families, union, scales, designs, benchmark, not args.fast)
    if not args.prepare_only:
        write_json(HERE / (args.prefix + "audit_summary.json"), dict(datasets=results, confirmation_seed=627018399,
                   boundary_seed=9927613, boundary_points_within_disclosed_family_support=True,
                   boundary_distribution_changed=True, targets_private_provisional=True))


if __name__ == "__main__":
    main()
