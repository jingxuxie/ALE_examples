import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "concept_1"
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import fisher_features


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize(reference, alternative, families, parameters, candidates, profile_module):
    report = profile_module.score_profiles(alternative, reference, families)
    report["champion_mean_intact_risk"] = float(reference["intact"].mean())
    report["champion_mean_single_loss_risk"] = float(reference["single"].mean())
    report["champion_mean_double_loss_risk"] = float(reference["double"].mean())
    report["single_loss_aggregate_inflation"] = float(reference["single"].mean() / reference["intact"].mean())
    report["double_loss_aggregate_inflation"] = float(reference["double"].mean() / reference["intact"].mean())
    ratio = reference["double"] / reference["intact"]
    report["double_loss_pointwise_ratio_quantiles"] = {str(quantile): float(np.quantile(ratio, quantile))
                                                       for quantile in [0., .5, .9, .99, 1.]}
    report["cases_more_than_tenfold_risk"] = int(np.count_nonzero(ratio > 10))
    report["dominant_failure_pairs"] = [
        dict(circuits=list(pair), count=count, experiments=[candidates[index] for index in pair])
        for pair, count in Counter(map(tuple, reference["double_worst_circuits"].tolist())).most_common(8)]
    worst = np.argsort(ratio)[-8:][::-1]
    report["strongest_cases"] = [dict(family=str(families[index]), parameters=parameters[index].tolist(),
        intact_risk=float(reference["intact"][index]), double_loss_risk=float(reference["double"][index]),
        ratio=float(ratio[index]), lost_circuits=reference["double_worst_circuits"][index].tolist()) for index in worst]
    return report


def cluster_failures(features, counts, reference, contract):
    roots = Counter()
    contributions = np.zeros(12)
    support = np.flatnonzero(counts)
    for index, model in enumerate(features):
        before = (model[support].T * (counts[support] * 64)) @ model[support] + np.eye(14) * 1e-10
        reduced = counts.copy()
        reduced[reference["double_worst_circuits"][index]] = 0
        kept = np.flatnonzero(reduced)
        after = (model[kept].T * (reduced[kept] * 64)) @ model[kept] + np.eye(14) * 1e-10
        before_covariance, after_covariance = np.linalg.inv(before), np.linalg.inv(after)
        diagonal = np.diag(after_covariance - before_covariance)[:12]
        contributions += diagonal
        total = float(diagonal.sum())
        known_readout_increment = float(np.trace(np.linalg.inv(after[:12, :12]) - np.linalg.inv(before[:12, :12])))
        dominant = int(np.argmax(diagonal))
        root = "readout/decay confounding" if total > 0 and (total - known_readout_increment) / total > .8 else (
            "concentrated coherent-angle information" if dominant < 9 else "concentrated decay-rate information")
        roots[root] += 1
    return dict(root_counts=dict(roots), mean_signal_variance_increments={
        contract["parameter_order"][index]: float(value / len(features)) for index, value in enumerate(contributions)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--per-family", type=int, default=500)
    args = parser.parse_args()
    started = time.monotonic()
    destination = ROOT / "adversary" / ("generation_" + str(args.generation))
    destination.mkdir(parents=True, exist_ok=True)
    champion_path = ROOT / "champions" / ("generation_" + str(args.generation)) / "design.json"
    proof_path = ROOT / "adversary/portfolio/resilience/best_double.json"
    counts = np.array(json.loads(champion_path.read_text())["batches"])
    proof_bytes = proof_path.read_bytes()
    (destination / "proof_design_initial.json").write_bytes(proof_bytes)
    proof = np.array(json.loads(proof_bytes)["batches"])
    candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
    contract = json.loads((ROOT / "participant/input/contract.json").read_text())
    profile_module = load_module(ROOT / "adversary/portfolio/resilience/metrics.py", "private_resilience_metrics")
    independent = load_module(Path(__file__).parent / "templates/loss_evaluate.py", "independent_loss_checker")
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as data:
        features, families, parameters = data["features"], data["families"], data["parameters"]
        reference = profile_module.profile(features, counts, direct=True)
        alternative = profile_module.profile(features, proof, direct=True)
        dense_intact, dense_loss, dense_pairs = independent.risk_profile(features, counts, 2, 64)
        if not np.allclose(dense_loss, reference["double"], rtol=2e-7, atol=1e-7):
            raise ValueError("independent loss implementations disagree")
        frozen = summarize(reference, alternative, families, parameters, candidates, profile_module)
        frozen["root_cause_clusters"] = cluster_failures(features, counts, reference, contract)
        frozen["independent_loss_max_relative_error"] = float(np.max(np.abs(dense_loss - reference["double"]) / reference["double"]))
    report = dict(champion_sha256=hashlib.sha256(champion_path.read_bytes()).hexdigest(),
                  alternative_sha256=hashlib.sha256(proof_bytes).hexdigest(),
                  original_contract_required_loss_resilience=False, frozen_benchmark=frozen,
                  selected_failure="two missing circuit records expose concentrated parameter information and readout/decay confounding")
    (destination / "champion_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print("frozen", frozen["double"], flush=True)
    with np.load(ROOT / "adversary/portfolio/broad_space.npz", allow_pickle=False) as data:
        selected = np.concatenate([np.flatnonzero(data["families"] == family)[:args.per_family] for family in np.unique(data["families"])])
        parameters, families = data["parameters"][selected], data["families"][selected]
    union = np.flatnonzero(counts + proof)
    subset = [candidates[index] for index in union]
    features = np.empty((len(parameters), len(union), 14))
    for index, operating_point in enumerate(parameters):
        features[index] = fisher_features(operating_point, subset)
        if index % 250 == 0:
            print("broad features", index, len(parameters), flush=True)
    reference = profile_module.profile(features, counts[union], direct=True)
    alternative = profile_module.profile(features, proof[union], direct=True)
    for label in ["single_worst_circuits", "double_worst_circuits"]:
        reference[label] = union[reference[label]]
        alternative[label] = union[alternative[label]]
    broad = summarize(reference, alternative, families, parameters, candidates, profile_module)
    broad["scenarios"] = len(parameters)
    broad["per_family"] = args.per_family
    report["broad_private_space"] = broad
    report["runtime_seconds"] = time.monotonic() - started
    np.savez_compressed(destination / "broad_champion_profiles.npz", parameters=parameters, families=families,
                        champion_intact=reference["intact"], champion_single=reference["single"],
                        champion_double=reference["double"], alternative_double=alternative["double"],
                        champion_worst_pairs=reference["double_worst_circuits"])
    (destination / "champion_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print("broad", broad["double"], flush=True)


if __name__ == "__main__":
    main()
