import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import signal
import sys
import time

import numpy as np
from scipy.special import logsumexp

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location("trusted_physics", ROOT / "evaluator" / "physics.py")
physics = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(physics)
SPEC = json.loads((ROOT / "participant" / "input" / "spec.json").read_text())


def write_json(path, document):
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def walsh_transform(values):
    transformed = np.array(values, dtype=np.float64, copy=True)
    stride = 1
    while stride < len(transformed):
        blocks = transformed.reshape(-1, 2, stride)
        first = blocks[:, 0, :].copy()
        second = blocks[:, 1, :].copy()
        blocks[:, 0, :] = first + second
        blocks[:, 1, :] = first - second
        stride *= 2
    return transformed


def all_sector_masses(probabilities, kernel_transform):
    return walsh_transform(walsh_transform(probabilities) * kernel_transform) / len(probabilities)


def timeout_handler(signum, frame):
    raise TimeoutError("bounded privileged search deadline reached")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--seed", type=int, default=180910606)
    parser.add_argument("--output", type=Path, default=ROOT / "adversary" / "search_run")
    parser.add_argument("--max-models", type=int, default=5000)
    arguments = parser.parse_args()
    if not 1 <= arguments.seconds <= 1200:
        raise ValueError("search must be bounded by at most twenty minutes")
    output = arguments.output.resolve()
    if not output.is_relative_to((ROOT / "adversary").resolve()):
        raise ValueError("private outputs must remain inside adversary")
    output.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    started = time.monotonic()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(arguments.seconds)
    generator = np.random.default_rng(arguments.seed)
    spins = physics.enumerate_spins(16)
    identifiers = np.arange(65536, dtype=np.uint32)
    bit_weights = np.left_shift(np.uint32(1), np.arange(16, dtype=np.uint32))
    edges = physics.torus_edges()
    edge_features = np.column_stack([spins[:, first] * spins[:, second] for first, second in edges])
    populations = ((spins + 1) / 2).sum(axis=1).astype(int)
    independent = np.ones(65536, dtype=bool)
    for first, second in edges:
        independent &= ~(((identifiers >> first) & 1).astype(bool) & ((identifiers >> second) & 1).astype(bool))
    independent_masks = identifiers[independent & (populations >= 4) & (populations <= 6)]
    kernel_transforms = {radius: walsh_transform((np.minimum(populations, 16 - populations) <= radius).astype(float)) for radius in (2, 3, 4)}
    state = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "seed": arguments.seed,
             "time_budget_seconds": arguments.seconds, "maximum_models": arguments.max_models,
             "models_drawn": 0, "admissible_models": 0, "cube_candidates": 0,
             "exact_candidates": 0, "best_score": -1.0, "passing_witness_found": False,
             "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "spec_sha256": hashlib.sha256((ROOT / "participant" / "input" / "spec.json").read_bytes()).hexdigest(),
             "numpy_version": np.__version__, "method": "seeded binary-disorder enumeration and ground-subcube logistic witnesses; exhaustive final metrics",
             "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}
    write_json(output / "run.json", state)
    best_score = -1.0
    best_candidate = None
    best_report = None
    coefficients = [math.log(9999) - 1e-12, 8.9, 8.5]
    beta_values = [2.0, 1.75, 2.25, 1.5, 2.5, 3.0, 1.25]
    seen = set()
    try:
        for model_index in range(arguments.max_models):
            if state["passing_witness_found"]:
                break
            state["models_drawn"] += 1
            bonds = generator.choice([-1, 1], size=32).tolist()
            frustrated = physics.frustrated_plaquettes(bonds)
            if not 4 <= frustrated <= 12:
                continue
            state["admissible_models"] += 1
            energy = -(edge_features @ np.asarray(bonds, dtype=float))
            ground_energy = float(energy.min())
            ground_identifiers = np.flatnonzero((energy == ground_energy) & (spins[:, 0] == -1))
            if len(ground_identifiers) < 24:
                continue
            generator.shuffle(ground_identifiers)
            ground_identifiers = ground_identifiers[:48]
            coupling_matrix = np.zeros((16, 16))
            for coupling, (first, second) in zip(bonds, edges):
                coupling_matrix[first, second] = coupling
                coupling_matrix[second, first] = coupling
            trial_beta = 2.0
            target = np.exp(-trial_beta * energy - logsumexp(-trial_beta * energy))
            target_sectors = all_sector_masses(target, kernel_transforms[4])
            if float(target_sectors.max()) < 0.35:
                continue
            target_cache = {}
            for ground_identifier in ground_identifiers:
                if state["passing_witness_found"]:
                    break
                center = spins[ground_identifier]
                free_spins = np.flatnonzero((coupling_matrix @ center) == 0)
                if len(free_spins) < 4:
                    continue
                free_mask = np.bitwise_or.reduce(bit_weights[free_spins])
                compatible = independent_masks[(independent_masks & free_mask) == independent_masks]
                if not len(compatible):
                    continue
                generator.shuffle(compatible)
                compatible = compatible[:8]
                for mask in compatible:
                    free = np.flatnonzero((mask >> np.arange(16)) & 1)
                    fixed = np.flatnonzero(~np.isin(np.arange(16), free))
                    signature = (tuple(bonds), int(mask), tuple(center[fixed].tolist()))
                    if signature in seen:
                        continue
                    seen.add(signature)
                    state["cube_candidates"] += 1
                    fixed_couplings = (coupling_matrix * center[:, None] * center[None, :])[:, fixed].sum(axis=1)
                    free_degrees = np.count_nonzero(coupling_matrix[:, free], axis=1)
                    penalty = (4 * fixed_couplings - coefficients[0]) ** 2 + 16 * free_degrees
                    anchor = int(fixed[np.argmax(penalty[fixed])])
                    order = [anchor] + [int(site) for site in fixed if site != anchor] + [int(site) for site in free]
                    match = spins[:, fixed] * center[fixed] * (spins[:, anchor] * center[anchor])[:, None]
                    mismatch_count = np.count_nonzero(match < 0, axis=1)
                    for coefficient in coefficients:
                        log_proposal = -(len(free) + 1) * math.log(2) - (len(fixed) - 1) * np.logaddexp(0.0, -coefficient) - coefficient * mismatch_count
                        proposal = np.exp(log_proposal)
                        proposal_sectors = all_sector_masses(proposal, kernel_transforms[4])
                        eligible = (proposal_sectors <= 0.001) & (target_sectors >= 0.345)
                        if not np.any(eligible):
                            continue
                        sector_identifier = int(np.argmax(np.where(eligible, target_sectors, -1)))
                        weights = np.zeros((16, 16))
                        for position, site in enumerate(order[1:len(fixed)], start=1):
                            weights[position, 0] = coefficient * center[site] * center[anchor]
                        for beta in beta_values:
                            if beta not in target_cache:
                                dimensionless = beta * energy
                                log_partition = float(logsumexp(-dimensionless))
                                target_beta = np.exp(-dimensionless - log_partition)
                                target_cache[beta] = (dimensionless, log_partition, target_beta)
                            dimensionless, log_partition, target_beta = target_cache[beta]
                            reward = dimensionless + log_proposal
                            mean_reward = float(proposal @ reward)
                            variance = float(proposal @ (reward - mean_reward) ** 2)
                            energy_error = abs(float((proposal - target_beta) @ dimensionless)) / 16
                            if variance > 0.35 or energy_error > 0.10:
                                continue
                            candidate = {"schema_version": 1, "bonds": bonds, "beta": beta, "order": order,
                                         "weights": weights.tolist(), "pattern": spins[sector_identifier].astype(int).tolist(), "radius": 4}
                            report = physics.evaluate_document(candidate, SPEC)
                            state["exact_candidates"] += 1
                            score = report["core_score"]
                            if score > best_score:
                                best_score = score
                                best_candidate = candidate
                                best_report = report
                                state.update(best_score=score, best_model_index=model_index,
                                             elapsed_seconds=time.monotonic() - started,
                                             passing_witness_found=bool(report["passed"]))
                                write_json(output / "witness.json", candidate)
                                write_json(output / "metrics.json", report)
                                write_json(output / "run.json", state)
                                print(json.dumps({"elapsed": state["elapsed_seconds"], "model": model_index,
                                                  "score": score, "passed": report["passed"], "metrics": report["metrics"]}), flush=True)
                            if report["passed"]:
                                state["passing_witness_found"] = True
                                break
                        if state["passing_witness_found"]:
                            break
                    if state["passing_witness_found"]:
                        break
            if model_index % 25 == 0:
                state["elapsed_seconds"] = time.monotonic() - started
                write_json(output / "run.json", state)
        state["termination"] = "passing witness" if state["passing_witness_found"] else "model bound exhausted"
    except TimeoutError:
        state["termination"] = "time bound exhausted"
    finally:
        signal.alarm(0)
        state["elapsed_seconds"] = time.monotonic() - started
        state["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(output / "run.json", state)
        if best_candidate is not None:
            write_json(output / "witness.json", best_candidate)
            write_json(output / "metrics.json", best_report)
        print(json.dumps(state), flush=True)


if __name__ == "__main__":
    main()
