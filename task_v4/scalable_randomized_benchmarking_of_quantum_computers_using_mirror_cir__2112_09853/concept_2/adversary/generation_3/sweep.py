import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

import math

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]
sys.path.insert(0, str(ROOT / "adversary/generation_2"))
import frozen_model as model
from private_transport import launch_command, run_episode
from sweep import RecordedEpisode, diagnostics, summarize

import numpy as np


def regularized_oracle(episode):
    supported = [pair for pair, coefficient in zip(episode.grid.pairs, episode.crosstalk) if coefficient > 0]
    edge_count = len(episode.grid.edges)
    base_variance = .005 ** 2 / 12
    if episode.family in ("anticorrelated", "spam_drift"):
        base_mean = .0085 / math.log(.010 / .0015)
        base_variance = (.010 ** 2 - .0015 ** 2) / (2 * math.log(.010 / .0015)) - base_mean ** 2
    variances = np.r_[.003 ** 2 / 12, np.full(edge_count, base_variance),
                      np.full(len(supported), (.015 if episode.family == "anticorrelated" else .025) ** 2 / 12)]
    information = np.diag(1 / variances)

    def features(matching):
        active = np.zeros(edge_count)
        active[matching] = 1.
        return np.r_[1., active, [active[first] * active[second] for first, second in supported]]

    for observation in episode.observations:
        depth = observation["depth"]
        if depth == 0:
            continue
        matching = observation["matching"]
        row = features(matching)
        signal = (1 - 2. ** (-episode.grid.qubits)) * episode.contrast(matching, observation["context"]) * math.exp(-depth * episode.log_rate(matching))
        probability = 2. ** (-episode.grid.qubits) + signal
        information += observation["shots"] * (depth * signal) ** 2 / (probability * (1 - probability)) * np.outer(row, row)
    rows = np.array([features(matching) for matching in episode.targets])
    derivatives = (1 - 4. ** (-episode.grid.qubits)) * np.exp(-np.array([episode.log_rate(matching) for matching in episode.targets]))
    gradients = rows * derivatives[:, None]
    variance = np.sum((gradients @ np.linalg.inv(information)) * gradients, axis=1)
    truths = np.array([episode.error_rate(matching) for matching in episode.targets])
    return float(np.mean(variance / (.003 + .1 * truths) ** 2))


def create_file(path, content):
    if path.exists():
        assert path.read_text() == content
        return
    patch = "*** Begin Patch\n*** Add File: " + str(path.relative_to(AREA)) + "\n"
    patch += "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch", patch + "*** End Patch\n"], cwd=AREA, check=True, stdout=subprocess.DEVNULL)


def execute(job):
    model.LIMITS["shots_budget"] = job["budget"]
    directory = AREA / "runs" / job["label"] / job["id"]
    directory.mkdir(parents=True, exist_ok=False)
    episode = RecordedEpisode(int(job["seed_hex"], 16), job["family"], job["shape"])
    artifact = AREA / "policies" / job["strategy"]
    stderr = directory / "stderr.txt"
    record = run_episode(episode, launch_command(artifact, "policy.py", job["isolation"]), artifact, stderr)
    record.update(job)
    if record["valid"]:
        record["diagnostics"] = diagnostics(episode, stderr)
        record["diagnostics"]["known_support_spam_prior_moment_fisher_proxy"] = regularized_oracle(episode)
        fit = json.loads(stderr.read_text().strip().splitlines()[-1])
        probabilities = {tuple(pair): probability for pair, probability in zip(fit["all_pairs"], fit["posterior_inclusion"])}
        supported = [pair for pair, coefficient in zip(episode.grid.pairs, episode.crosstalk) if coefficient > 0]
        record["diagnostics"]["mean_true_support_posterior_inclusion"] = sum(probabilities.get(tuple(pair), 0.) for pair in supported) / len(supported)
    else:
        record["stderr"] = stderr.read_text()[-4000:]
    record["targets_sha256"] = hashlib.sha256(json.dumps(episode.targets).encode()).hexdigest()
    (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budgets", type=int, nargs="+", default=[6000, 3000, 2000, 1500, 1000])
    parser.add_argument("--strategies", nargs="+", default=["proportional", "adaptive"])
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--isolation", choices=("audit", "bwrap"), default="audit")
    parser.add_argument("--label", required=True)
    parser.add_argument("--seed-set", default="exploration")
    arguments = parser.parse_args()
    assert 1 <= arguments.workers <= 4
    source = (ROOT / "champions/generation_2/policy.py").read_text()
    assert source.count("self.used / 12000") == 1
    source = source.replace("self.used / 12000", 'self.used / self.hello["limits"]["shots_budget"]')
    for strategy in arguments.strategies:
        assert strategy in ("proportional", "adaptive")
        directory = AREA / "policies" / strategy
        directory.mkdir(parents=True, exist_ok=True)
        create_file(directory / "policy.py", (AREA / "policy.py").read_text())
        create_file(directory / "champion_policy.py", source)
        create_file(directory / "allocation.json", json.dumps({"allocation": strategy}) + "\n")
        for name in ("sampler.so", "sampler.cpp"):
            original = ROOT / "champions/generation_2" / name
            target = directory / name
            if target.exists():
                assert target.read_bytes() == original.read_bytes()
            else:
                shutil.copyfile(original, target)
    seed_path = AREA / ("cases_" + arguments.seed_set + ".json")
    if seed_path.exists():
        cases = json.loads(seed_path.read_text())
    else:
        cases = [{"family": family, "shape": list(shape), "replica": replica, "seed_hex": secrets.token_hex(16)}
                 for family in model.FAMILIES for shape in model.SHAPES for replica in range(arguments.replicas)]
        seed_path.write_text(json.dumps(cases, indent=2) + "\n")
    jobs = [dict(case, budget=budget, strategy=strategy, isolation=arguments.isolation,
                 label=arguments.label, id=str(budget) + "_" + strategy + "_" + str(case_index))
            for budget in arguments.budgets for strategy in arguments.strategies for case_index, case in enumerate(cases)]
    started = time.monotonic()
    records = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [executor.submit(execute, job) for job in jobs]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 12 == 0:
                print(json.dumps({"completed": len(records), "total": len(jobs),
                                  "latest": records[-1]["budget"], "valid": all(record["valid"] for record in records)}), flush=True)
    report = {"calibration_only": arguments.isolation != "bwrap", "seed_set": arguments.seed_set,
              "seed_manifest_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              "wall_seconds": time.monotonic() - started, "sampler_rescaled": False,
              "summaries": summarize(records), "records": records}
    (AREA / (arguments.label + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
