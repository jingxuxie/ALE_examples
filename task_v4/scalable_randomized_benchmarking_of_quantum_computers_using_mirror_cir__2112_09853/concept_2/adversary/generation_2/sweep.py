import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

import frozen_model as model
from private_transport import launch_command, run_episode


ROOT = Path(__file__).resolve().parent
STRATEGIES = {
    "coverage_full": {"pair_shots_minimum": 64, "thin_controls": False},
    "coverage_thin": {"pair_shots_minimum": 64, "thin_controls": True},
    "precision_thin": {"pair_shots_minimum": 128, "thin_controls": True},
}


class RecordedEpisode(model.Episode):
    def __init__(self, seed, family, shape):
        super().__init__(seed, family, shape)
        self.observations = []

    def handle(self, message):
        response = super().handle(message)
        if response["type"] == "observation":
            self.observations.append(response)
        return response


def diagnostics(episode, stderr_path):
    support_indices = np.flatnonzero(episode.crosstalk > 0)
    support = [episode.grid.pairs[index] for index in support_indices]
    edge_count = len(episode.grid.edges)

    def features(matching):
        active = np.zeros(edge_count)
        active[matching] = 1.
        return np.r_[1., active, [active[first] * active[second] for first, second in support]]

    information = np.zeros((edge_count + 1 + len(support),) * 2)
    coverage = np.zeros(len(support))
    contrasts = []
    pair_contrast_differences = []
    previous = None
    for observation in episode.observations:
        matching, depth = observation["matching"], observation["depth"]
        contrast = episode.contrast(matching, observation["context"])
        contrasts.append(contrast)
        if depth == 0:
            previous = observation
            continue
        row = features(matching)
        coverage += row[edge_count + 1:]
        signal = (1 - 2. ** (-episode.grid.qubits)) * contrast * math.exp(-depth * episode.log_rate(matching))
        probability = 2. ** (-episode.grid.qubits) + signal
        weight = observation["shots"] * (depth * signal) ** 2 / max(1e-15, probability * (1-probability))
        information += weight * np.outer(row, row)
        if previous is not None and previous["matching"] == matching:
            pair_contrast_differences.append(abs(contrast - episode.contrast(matching, previous["context"])))
    eigenvalues, eigenvectors = np.linalg.eigh(information)
    retained = eigenvalues > max(1e-10, eigenvalues[-1] * 1e-10)
    target_rows = np.array([features(matching) for matching in episode.targets])
    target_null = target_rows @ eigenvectors[:, ~retained]
    identifiable = target_null.size == 0 or float(np.max(np.abs(target_null))) < 1e-6
    oracle_mse = None
    if identifiable:
        inverse = (eigenvectors[:, retained] / eigenvalues[retained]) @ eigenvectors[:, retained].T
        truths = np.array([episode.error_rate(matching) for matching in episode.targets])
        derivatives = (1 - 4. ** (-episode.grid.qubits)) * np.exp(-np.array([episode.log_rate(matching) for matching in episode.targets]))
        gradients = target_rows * derivatives[:, None]
        variance = np.sum((gradients @ inverse) * gradients, axis=1)
        oracle_mse = float(np.mean(variance / (0.003 + 0.1 * truths) ** 2))
    fit = json.loads(stderr_path.read_text().strip().splitlines()[-1])
    selected = set(map(tuple, fit["selected_pairs"]))
    truth_support = set(support)
    return {"support_size": len(support), "supported_pairs_unobserved": int(np.sum(coverage == 0)),
            "minimum_support_exposure": float(coverage.min()), "mean_support_exposure": float(coverage.mean()),
            "support_recall": len(selected & truth_support) / len(truth_support),
            "support_precision": len(selected & truth_support) / max(1, len(selected)),
            "selected_support_size": len(selected),
            "base_rmse": float(np.sqrt(np.mean((np.array(fit["base"]) - episode.base) ** 2))),
            "depth_zero_shots": sum(row["shots"] for row in episode.observations if row["depth"] == 0),
            "max_adjacent_spam_change": max(pair_contrast_differences, default=0.),
            "oracle_known_support_known_spam_identifiable": identifiable,
            "oracle_local_fisher_normalized_mse": oracle_mse,
            "oracle_caveat": "Optimistic local Fisher proxy with known support and SPAM, not a certified attainable score or a global Bayesian bound."}


def execute(job):
    model.LIMITS["shots_budget"] = job["budget"]
    directory = ROOT / "runs" / job["label"] / job["id"]
    directory.mkdir(parents=True, exist_ok=False)
    episode = RecordedEpisode(int(job["seed_hex"], 16), job["family"], job["shape"])
    artifact = ROOT / "policies" / job["strategy"]
    stderr_path = directory / "stderr.txt"
    record = run_episode(episode, launch_command(artifact, "policy.py", job["isolation"]), artifact, stderr_path)
    record.update(job)
    if record["valid"]:
        record["diagnostics"] = diagnostics(episode, stderr_path)
    else:
        record["stderr"] = stderr_path.read_text()[-4000:]
    record["targets_sha256"] = hashlib.sha256(json.dumps(episode.targets).encode()).hexdigest()
    (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarize(records):
    summaries = []
    for budget, strategy in sorted({(record["budget"], record["strategy"]) for record in records}, reverse=True):
        group = [record for record in records if record["budget"] == budget and record["strategy"] == strategy]
        families = {}
        for family in model.FAMILIES:
            members = [record for record in group if record["family"] == family]
            valid = bool(members) and all(record["valid"] for record in members)
            mse = float(np.mean([record["normalized_mse"] for record in members])) if valid else None
            families[family] = {"valid": valid, "score": 1 / (1 + mse) if valid else 0.,
                                "normalized_mse": mse, "episodes": len(members)}
        average = float(np.mean([family["score"] for family in families.values()]))
        worst = min(family["score"] for family in families.values())
        valid = all(record["valid"] for record in group)
        scores_meet_target = valid and average >= .5 and worst >= 1 / 2.5625
        diagnostics_rows = [record["diagnostics"] for record in group if record["valid"]]
        oracle = [row["oracle_local_fisher_normalized_mse"] for row in diagnostics_rows if row["oracle_local_fisher_normalized_mse"] is not None]
        summaries.append({"budget": budget, "strategy": strategy, "valid": valid,
                          "valid_episodes": sum(record["valid"] for record in group), "episodes": len(group),
                          "average_score": average, "worst_family_score": worst, "families": families,
                          "quality_target_met": scores_meet_target,
                          "certified_isolated_pass": scores_meet_target and all(record["isolation"] == "bwrap" for record in group),
                          "mean_support_recall": float(np.mean([row["support_recall"] for row in diagnostics_rows])) if diagnostics_rows else None,
                          "mean_unobserved_support": float(np.mean([row["supported_pairs_unobserved"] for row in diagnostics_rows])) if diagnostics_rows else None,
                          "oracle_proxy_mean_normalized_mse": float(np.mean(oracle)) if oracle else None,
                          "oracle_proxy_identifiable_episodes": len(oracle),
                          "max_cpu_seconds": max(record["cpu_seconds"] for record in group),
                          "max_wall_seconds": max(record["wall_seconds"] for record in group)})
    return summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budgets", type=int, nargs="+", default=[240000, 48000, 24000, 12000, 8000, 6000, 4000])
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--isolation", choices=["audit", "bwrap"], default="audit")
    parser.add_argument("--label", required=True)
    parser.add_argument("--seed-set", default="exploration")
    arguments = parser.parse_args()
    assert 1 <= arguments.workers <= 4
    for strategy, settings in STRATEGIES.items():
        directory = ROOT / "policies" / strategy
        directory.mkdir(parents=True, exist_ok=True)
        for source, target in ((ROOT / "budget_policy.py", directory / "policy.py"),
                               (ROOT / "champion_policy.py", directory / "champion_policy.py")):
            if target.exists():
                assert target.read_bytes() == source.read_bytes()
            else:
                shutil.copyfile(source, target)
        allocation = directory / "allocation.json"
        if allocation.exists():
            assert json.loads(allocation.read_text()) == settings
        else:
            allocation.write_text(json.dumps(settings))
    seed_path = ROOT / ("cases_" + arguments.seed_set + ".json")
    if seed_path.exists():
        cases = json.loads(seed_path.read_text())
    else:
        cases = [{"family": family, "shape": list(shape), "replica": replica,
                  "seed_hex": secrets.token_hex(16)} for family in model.FAMILIES
                 for shape in model.SHAPES for replica in range(arguments.replicas)]
        seed_path.write_text(json.dumps(cases, indent=2) + "\n")
    jobs = []
    for budget in arguments.budgets:
        for strategy in arguments.strategies:
            for case_index, case in enumerate(cases):
                jobs.append(dict(case, budget=budget, strategy=strategy, isolation=arguments.isolation,
                                 label=arguments.label, id=str(budget) + "_" + strategy + "_" + str(case_index)))
    started = time.monotonic()
    records = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [executor.submit(execute, job) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 12 == 0:
                print(json.dumps({"completed": len(records), "total": len(jobs)}), flush=True)
    report = {"calibration_only": arguments.isolation != "bwrap", "seed_set": arguments.seed_set,
              "seed_manifest_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              "wall_seconds": time.monotonic() - started, "summaries": summarize(records), "records": records}
    (ROOT / (arguments.label + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
