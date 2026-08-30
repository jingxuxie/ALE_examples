import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, ROOT, REFERENCE, TARGETS, covariance, profile, score_profiles

sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features


def root_clusters(features, counts, result, families, parameters, union, candidates, contract):
    rows = features * 8
    information, inverted, intact = covariance(rows, counts)
    original_diagonal = np.diagonal(inverted[:, :12, :12], axis1=1, axis2=2)
    summary = {}
    for label in ["single", "double"]:
        lost_cases = result[label + "_worst_circuits"]
        reduced = information.copy()
        for deletion in range(lost_cases.shape[1]):
            local = lost_cases[:, deletion]
            vectors = rows[np.arange(len(rows)), local]
            reduced -= counts[local, None, None] * (vectors[:, :, None] @ vectors[:, None, :])
        covariance_after = np.linalg.inv(reduced)
        increments = np.diagonal(covariance_after[:, :12, :12], axis1=1, axis2=2) - original_diagonal
        eigenvalues = np.linalg.eigvalsh(reduced)
        global_cases = union[lost_cases]
        histogram = Counter(tuple(case) for case in global_cases)
        groups = []
        for case, frequency in histogram.most_common(8):
            mask = np.all(global_cases == np.array(case)[None], axis=1)
            mean_increment = increments[mask].mean(axis=0)
            ranked = np.argsort(mean_increment)[::-1]
            groups.append(dict(circuits=[int(index) for index in case],
                               circuit_definitions=[candidates[index] for index in case],
                               operating_points=frequency, family_counts=dict(Counter(str(family) for family in families[mask])),
                               mean_after_loss_risk=float(result[label][mask].mean()),
                               dominant_parameter_increments=[dict(parameter=contract["parameter_order"][index],
                                                                    mean_increment=float(mean_increment[index]))
                                                              for index in ranked[:4]]))
        worst = int(np.argmax(result[label]))
        summary[label] = dict(groups=groups, minimum_worst_loss_information_eigenvalue=float(eigenvalues.min()),
                              worst_point=dict(family=str(families[worst]), parameters=parameters[worst].tolist(),
                                               lost_circuits=[int(index) for index in global_cases[worst]],
                                               intact_risk=float(intact[worst]), after_loss_risk=float(result[label][worst])))
    return summary


def evaluate_dataset(name, features, families, parameters, designs, union, benchmark):
    profiles = {label: profile(features, counts[union], direct=True) for label, counts in designs.items()}
    results = {}
    clusters = {}
    arrays = dict(families=families, parameters=parameters, candidate_union=union)
    for label, counts in designs.items():
        result = profiles[label]
        fast = profile(features, counts[union], direct=False)
        comparison = {mode: float(np.max(np.abs(fast[mode] / result[mode] - 1))) for mode in ["single", "double"]}
        score = score_profiles(result, profiles["reference"], families)
        score["direct_inverse_vs_woodbury_relative_error"] = comparison
        score["numerical_check_passed"] = max(comparison.values()) < 1e-7
        score["scenarios"] = len(families)
        score["every_deletion_case_directly_inverted"] = True
        score["candidate_design_sha256"] = hashlib.sha256((json.dumps({"batches": counts.tolist()}) + "\n").encode()).hexdigest()
        results[label] = score
        for mode in ["intact", "single", "double"]:
            arrays[label + "_" + mode + "_risks"] = result[mode]
        for mode in ["single", "double"]:
            arrays[label + "_" + mode + "_worst_circuits"] = union[result[mode + "_worst_circuits"]]
        clusters[label] = root_clusters(features, counts[union], result, families, parameters, union,
                                        benchmark.candidates, benchmark.contract)
        print(json.dumps(dict(dataset=name, design=label, intact_ratio=score["intact_mean_ratio"],
                              single_core=score["single"]["core_score"], single_worst=score["single"]["worst_family_score"],
                              single_pass=score["single"]["passed"], double_core=score["double"]["core_score"],
                              double_worst=score["double"]["worst_family_score"], double_pass=score["double"]["passed"],
                              numerical_check_passed=score["numerical_check_passed"])), flush=True)
    np.savez_compressed(HERE / f"{name}_profiles.npz", **arrays)
    (HERE / f"{name}_scores.json").write_text(json.dumps(results, indent=2) + "\n")
    (HERE / f"{name}_root_clusters.json").write_text(json.dumps(clusters, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-family", type=int, default=500)
    args = parser.parse_args()
    started = time.monotonic()
    benchmark = Benchmark()
    frozen = json.loads((HERE / "contract.json").read_text())
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == frozen["reference_design_sha256"]
    designs = {"reference": benchmark.reference_counts}
    for label in ["single", "double"]:
        data = json.loads((HERE / f"best_{label}.json").read_text())
        counts = np.array(data["batches"])
        benchmark.validate(counts)
        designs[label] = counts
        (HERE / f"audited_{label}_design.json").write_text(json.dumps(data) + "\n")
    union = np.flatnonzero(np.any(np.array(list(designs.values())) > 0, axis=0))
    hidden = evaluate_dataset("hidden", benchmark.features[:, union], benchmark.families, benchmark.parameters,
                              designs, union, benchmark)
    broad_scores = None
    if args.per_family:
        with np.load(HERE.parent / "broad_space.npz", allow_pickle=False) as broad:
            selected = np.concatenate([np.flatnonzero(broad["families"] == family)[:args.per_family] for family in FAMILIES])
            parameters = broad["parameters"][selected].copy()
            families = broad["families"][selected].copy()
        selected_candidates = [benchmark.candidates[index] for index in union]
        features = []
        for index, parameter in enumerate(parameters):
            features.append(fisher_features(parameter, selected_candidates))
            if (index + 1) % args.per_family == 0:
                print(json.dumps(dict(event="audit_features", scenarios=index + 1,
                                      seconds=time.monotonic() - started)), flush=True)
        features = np.array(features)
        np.savez_compressed(HERE / "broad_features.npz", features=features, parameters=parameters,
                            families=families, candidate_union=union)
        broad_scores = evaluate_dataset("broad", features, families, parameters, designs, union, benchmark)
    report = dict(targets=TARGETS, hidden=hidden, broad=broad_scores,
                  separate_single_and_double_designs=True,
                  broad_operating_points_used_for_optimization=False,
                  original_artifacts_unchanged=True, fresh_attempts_read=False,
                  seconds=time.monotonic() - started, reference_design_sha256=frozen["reference_design_sha256"])
    (HERE / "audit_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(event="audit_complete", seconds=report["seconds"])), flush=True)


if __name__ == "__main__":
    main()
