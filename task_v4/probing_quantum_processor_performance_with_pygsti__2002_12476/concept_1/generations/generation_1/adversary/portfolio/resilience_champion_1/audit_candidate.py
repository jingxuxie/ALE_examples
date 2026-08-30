import argparse
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from rebased import Benchmark, HERE, OLD, ROOT, profile, score_profiles, write_json
from audit import root_clusters

sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features, sample_parameters


def prepare_features(name, desired_union, benchmark):
    path = HERE / f"{name}_features.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as source:
            parameters = source["parameters"].copy()
            families = source["families"].copy()
            available_union = source["candidate_union"].copy()
            available_features = source["features"].copy()
    elif name == "broad":
        with np.load(OLD / "broad_features.npz", allow_pickle=False) as source:
            parameters = source["parameters"].copy()
            families = source["families"].copy()
            available_union = source["candidate_union"].copy()
            available_features = source["features"].copy()
    else:
        rng = np.random.default_rng(71389201 if name == "fresh" else 99583321)
        families = np.repeat(np.array(FAMILIES), 100)
        parameters = np.array([sample_parameters(rng, str(family)) for family in families])
        available_union = np.empty(0, dtype=int)
        available_features = np.empty((len(families), 0, 14))
    union = np.union1d(desired_union, available_union)
    features = np.empty((len(families), len(union), 14))
    positions = np.searchsorted(union, available_union)
    features[:, positions] = available_features
    missing = np.setdiff1d(union, available_union)
    positions = np.searchsorted(union, missing)
    candidates = [benchmark.candidates[index] for index in missing]
    for index, operating_point in enumerate(parameters):
        if len(missing):
            features[index, positions] = fisher_features(operating_point, candidates)
        if (index + 1) % 300 == 0:
            print(json.dumps(dict(event="features", dataset=name, complete=index + 1,
                                  total=len(parameters), missing_candidates=len(missing))), flush=True)
    np.savez_compressed(path, parameters=parameters, families=families,
                        candidate_union=union, features=features)
    return features, families, parameters, union


def audit_dataset(name, features, families, parameters, union, designs, benchmark):
    profiles = {label: profile(features, counts[union], direct=True) for label, counts in designs.items()}
    results = {}
    arrays = dict(parameters=parameters, families=families, candidate_union=union)
    clusters = {}
    for label, counts in designs.items():
        result = profiles[label]
        fast = profile(features, counts[union], direct=False)
        score = score_profiles(result, profiles["reference"], families)
        score["direct_inverse_vs_woodbury_relative_error"] = {
            mode: float(np.max(np.abs(fast[mode] / result[mode] - 1))) for mode in ["single", "double"]}
        score.update(scenarios=len(families), every_pair_directly_inverted=True,
                     core_score=score["double"]["core_score"], worst_family_score=score["double"]["worst_family_score"],
                     passed=score["double"]["passed"], design_batches=counts.tolist())
        for mode in ["intact", "single", "double"]:
            arrays[label + "_" + mode + "_risks"] = result[mode]
        for mode in ["single", "double"]:
            arrays[label + "_" + mode + "_worst_circuits"] = union[result[mode + "_worst_circuits"]]
        score["two_loss_mean_inflation_over_intact"] = float(np.mean(result["double"] / result["intact"]))
        score["two_loss_max_inflation_over_intact"] = float(np.max(result["double"] / result["intact"]))
        results[label] = score
        clusters[label] = root_clusters(features, counts[union], result, families, parameters, union,
                                        benchmark.candidates, benchmark.contract)
        print(json.dumps(dict(event="audit", dataset=name, design=label, core=score["core_score"],
                              worst_family=score["worst_family_score"], intact_ratio=score["intact_mean_ratio"],
                              passed=score["passed"], numerical=score["direct_inverse_vs_woodbury_relative_error"])), flush=True)
    np.savez_compressed(HERE / f"{name}_profiles.npz", **arrays)
    write_json(HERE / f"{name}_scores.json", results)
    write_json(HERE / f"{name}_root_clusters.json", clusters)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--datasets", nargs="+", default=["hidden", "broad", "fresh"])
    parser.add_argument("--submission", default="design.json")
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()
    started = time.monotonic()
    benchmark = Benchmark()
    benchmark.freeze()
    designs = {"reference": benchmark.reference_counts}
    if not args.prepare:
        designs["candidate"] = np.array(json.loads((HERE / args.submission).read_text())["batches"])
        benchmark.validate(designs["candidate"])
    required = np.unique(np.concatenate([np.flatnonzero(counts) for counts in designs.values()]))
    if args.prepare:
        available_path = HERE / "broad_features.npz"
        if not available_path.exists():
            available_path = OLD / "broad_features.npz"
        with np.load(available_path, allow_pickle=False) as source:
            required = np.union1d(required, source["candidate_union"])
    summary = {}
    for name in args.datasets:
        if name == "hidden":
            features, families, parameters, union = benchmark.features, benchmark.families, benchmark.parameters, np.arange(840)
        else:
            features, families, parameters, union = prepare_features(name, required, benchmark)
        if not args.prepare:
            summary[name] = audit_dataset(args.prefix + name, features, families, parameters, union, designs, benchmark)
    if not args.prepare:
        write_json(HERE / (args.prefix + "audit_summary.json"), dict(datasets=summary,
                   audit_seconds=time.monotonic() - started, fresh_seed=71389201,
                   confirmation_seed=99583321, broad_used_for_selection=bool(args.prefix),
                   fresh_draws_never_used_for_search=True))
    print(json.dumps(dict(event="done", seconds=time.monotonic() - started)), flush=True)


if __name__ == "__main__":
    main()
