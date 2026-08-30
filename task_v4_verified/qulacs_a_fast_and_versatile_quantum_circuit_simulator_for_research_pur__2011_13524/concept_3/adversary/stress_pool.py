import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys

import numpy as np


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "participant" / "input"
sys.path.insert(0, str(INPUT))

from simulator import BOUNDS, FAMILIES, PARAMETERS, parameter_dict, predictive_grid, probabilities, sample_prior, validate_estimate


SUPPORTS = {
    "resolved": {
        "bounds": [[0.35, 2.05], [0.35, 2.05], [0.025, 0.16], [0.10, 0.28], [0.10, 0.28],
                   [-0.65, 0.65], [0.78, 0.90], [0.78, 0.90], [-0.06, 0.06], [-0.06, 0.06]],
        "minimum_absolute_frequency_gap": 0.35,
    },
    "close_coupled": {
        "bounds": [[0.45, 1.90], [0.475, 2.00], [0.10, 0.20], [0.16, 0.34], [0.16, 0.34],
                   [-0.85, 0.85], [0.68, 0.88], [0.68, 0.88], [-0.08, 0.08], [-0.08, 0.08]],
        "signed_frequency_gap": [0.025, 0.10],
        "absolute_rho": [0.40, 0.85],
    },
    "low_visibility_spam": {
        "bounds": [[0.35, 2.05], [0.35, 2.05], [0.025, 0.20], [0.24, 0.44], [0.24, 0.44],
                   [-0.85, 0.85], [0.50, 0.68], [0.50, 0.68], [-0.085, 0.085], [-0.085, 0.085]],
        "minimum_absolute_frequency_gap": 0.15,
    },
}


def edge_scores(family, candidates):
    bounds = np.array(SUPPORTS[family]["bounds"])
    unit = (candidates - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
    frequency_mean = unit[:, :2].mean(axis=1)
    gap = np.abs(candidates[:, 0] - candidates[:, 1])
    gap_unit = (gap - gap.min()) / max(float(np.ptp(gap)), 1e-12)
    opposite_biases = candidates[:, 8] * candidates[:, 9] < 0
    bias_extent = np.abs(candidates[:, 8:10] / bounds[8:10, 1]).mean(axis=1)
    return {
        "low_frequency_weak_coupling": -(frequency_mean + unit[:, 2]),
        "high_frequency_strong_coupling": frequency_mean + unit[:, 2],
        "minimum_gap_strong_coupling": -gap_unit + 0.15 * unit[:, 2],
        "low_visibility_fast_dephasing": (1 - unit[:, 6:8]).mean(axis=1) + unit[:, 3:5].mean(axis=1),
        "positive_correlation": candidates[:, 5],
        "negative_correlation": -candidates[:, 5],
        "opposite_extreme_biases": np.where(opposite_biases, bias_extent, -np.inf),
        "asymmetric_envelopes": np.abs(unit[:, 3] - unit[:, 4]) + np.abs(unit[:, 6] - unit[:, 7]),
    }


def seed128(rng):
    return int.from_bytes(rng.bytes(16), "big")


def validate_pool(pool):
    cases = pool["cases"]
    if len(cases) != 36 or Counter(case["family"] for case in cases) != Counter({family: 12 for family in FAMILIES}):
        raise ValueError("pool must contain exactly twelve cases per disclosed family")
    if len({case["id"] for case in cases}) != 36:
        raise ValueError("case ids must be unique")
    all_seeds = []
    parameter_keys = set()
    grid = predictive_grid()
    probability_minimum = 1.0
    probability_maximum = 0.0
    for case in cases:
        if set(case) != {"id", "family", "parameters", "screening_seeds", "confirmation_seed"}:
            raise ValueError("unexpected case schema")
        theta = validate_estimate({"type": "estimate", "parameters": case["parameters"]})
        support = SUPPORTS[case["family"]]
        bounds = np.array(support["bounds"])
        if np.any(theta < bounds[:, 0] - 1e-12) or np.any(theta > bounds[:, 1] + 1e-12):
            raise ValueError("latent parameter outside its published family support")
        gap = theta[1] - theta[0]
        if "minimum_absolute_frequency_gap" in support and abs(gap) < support["minimum_absolute_frequency_gap"] - 1e-12:
            raise ValueError("frequency gap outside its family support")
        if "signed_frequency_gap" in support:
            lower_gap, upper_gap = support["signed_frequency_gap"]
            if not lower_gap - 1e-12 <= gap <= upper_gap + 1e-12:
                raise ValueError("signed frequency gap outside its family support")
            lower_rho, upper_rho = support["absolute_rho"]
            if not lower_rho <= abs(theta[5]) <= upper_rho:
                raise ValueError("correlation outside the disconnected family support")
        if theta[6] + abs(theta[8]) > 1 or theta[7] + abs(theta[9]) > 1 or abs(theta[5]) >= 1:
            raise ValueError("unphysical SPAM or Gaussian covariance")
        parameter_key = tuple(theta)
        if parameter_key in parameter_keys:
            raise ValueError("duplicate latent parameter vector")
        parameter_keys.add(parameter_key)
        predicted = probabilities(theta, grid)
        if not np.all(np.isfinite(predicted)) or np.any(predicted < 0) or np.any(predicted > 1):
            raise ValueError("unphysical predictive probability")
        probability_minimum = min(probability_minimum, float(predicted.min()))
        probability_maximum = max(probability_maximum, float(predicted.max()))
        if len(case["screening_seeds"]) != 3:
            raise ValueError("each case requires three screening seeds")
        seeds = case["screening_seeds"] + [case["confirmation_seed"]]
        if any(type(seed) is not int or not 0 <= seed < 2 ** 128 for seed in seeds):
            raise ValueError("outcome seeds must be 128-bit nonnegative integers")
        all_seeds.extend(seeds)
    if len(set(all_seeds)) != 144:
        raise ValueError("screening and confirmation outcome seeds must all be distinct")
    return {"cases": 36, "unique_outcome_seeds": 144, "probability_grid_size_per_case": len(grid),
            "probability_minimum": probability_minimum, "probability_maximum": probability_maximum,
            "family_supports_valid": True, "physical_covariances_and_readout_valid": True,
            "outcomes_generated": 0}


def generate_pool(audit_seed, candidates_per_family):
    parameter_stream, screening_stream, confirmation_stream = np.random.SeedSequence(audit_seed).spawn(3)
    family_streams = parameter_stream.spawn(len(FAMILIES))
    screening_rng = np.random.default_rng(screening_stream)
    confirmation_rng = np.random.default_rng(confirmation_stream)
    cases = []
    selection_audit = {}
    sampled_bounds = {}
    for family, stream in zip(FAMILIES, family_streams):
        rng = np.random.default_rng(stream)
        bulk = [sample_prior(family, rng) for _ in range(4)]
        candidates = np.array([sample_prior(family, rng) for _ in range(candidates_per_family)])
        selected = [("bulk_iid", index, theta, None) for index, theta in enumerate(bulk)]
        used = set()
        for label, scores in edge_scores(family, candidates).items():
            available = scores.copy()
            if used:
                available[list(used)] = -np.inf
            index = int(np.argmax(available))
            used.add(index)
            selected.append((label, index, candidates[index], float(scores[index])))
        for position, (label, index, theta, selection_score) in enumerate(selected, start=1):
            identifier = "stress-" + family + "-" + str(position).zfill(2)
            cases.append({"id": identifier, "family": family, "parameters": parameter_dict(theta),
                          "screening_seeds": [seed128(screening_rng) for _ in range(3)],
                          "confirmation_seed": seed128(confirmation_rng)})
            selection_audit[identifier] = {"coverage": label, "draw_index": index,
                                           "draw_source": "bulk_prior" if label == "bulk_iid" else "edge_prior_candidates",
                                           "latent_selection_score": selection_score}
        values = np.array([theta for _, _, theta, _ in selected])
        gaps = np.abs(values[:, 0] - values[:, 1])
        sampled_bounds[family] = {
            "parameter_min_max": {name: [float(values[:, index].min()), float(values[:, index].max())]
                                  for index, name in enumerate(PARAMETERS)},
            "absolute_frequency_gap_min_max": [float(gaps.min()), float(gaps.max())],
            "positive_rho_count": int(np.sum(values[:, 5] > 0)),
            "negative_rho_count": int(np.sum(values[:, 5] < 0)),
            "bulk_count": 4, "edge_count": 8,
        }
    pool = {
        "metadata": {
            "schema": "correlated-ramsey-stress-pool-v1", "audit_seed": audit_seed,
            "purpose": "private generation-only sidecar; no fresh-agent attempt and no active-suite change",
            "candidates_per_family": candidates_per_family, "cases_per_family": 12,
            "screening_replicates": 3, "held_out_confirmation_replicates": 1,
            "sampler": "participant/input/simulator.py:sample_prior",
            "simulator_sha256": hashlib.sha256((INPUT / "simulator.py").read_bytes()).hexdigest(),
            "numpy_version": np.__version__, "bit_generator": "PCG64",
            "parameter_order": list(PARAMETERS), "global_parameter_bounds": BOUNDS.tolist(),
            "family_supports": SUPPORTS, "sampled_bounds": sampled_bounds,
            "seed_domains": {"parameter_stream": [0], "screening_stream": [1], "confirmation_stream": [2]},
            "selection": "Four unconditional iid prior draws plus eight unique extrema of declared latent-only coverage scores per family. All candidates are unmodified sample_prior draws. This is a curated stress pool, not an iid draw from the family mixture.",
            "selection_audit": selection_audit,
            "confirmation_policy": "Use all three screening seeds for aggregate and repeatability checks. Freeze case selection before evaluating confirmation seeds; never select or discard cases based on confirmation outcomes or one unlucky screening seed.",
            "outcome_access": "No binomial outcomes, strategies, scores, evaluator modules, or active private suite are read or evaluated by this generator.",
        },
        "cases": cases,
    }
    pool["metadata"]["validation"] = validate_pool(pool)
    return pool


def main():
    parser = argparse.ArgumentParser(description="Generate only the private same-support latent stress pool")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--candidates-per-family", type=int, default=8192)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    output = Path(__file__).with_suffix(".json")
    if arguments.check:
        pool = json.loads(output.read_text())
        validation = validate_pool(pool)
        replay = generate_pool(pool["metadata"]["audit_seed"], pool["metadata"]["candidates_per_family"])
        if replay["cases"] != pool["cases"]:
            raise ValueError("audit seed does not reproduce all latent parameters and outcome seeds")
        print(json.dumps(dict(validation, deterministic_replay=True), allow_nan=False))
        return
    if output.exists():
        raise SystemExit("Refusing to overwrite the existing stress pool; --check is read-only")
    if arguments.candidates_per_family < 64:
        parser.error("at least 64 latent candidates per family are required")
    audit_seed = secrets.randbits(128) if arguments.seed is None else arguments.seed
    if audit_seed < 0:
        parser.error("seed must be nonnegative")
    pool = generate_pool(audit_seed, arguments.candidates_per_family)
    pool["metadata"]["created_utc"] = datetime.now(timezone.utc).isoformat()
    with output.open("x") as handle:
        json.dump(pool, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(dict(pool["metadata"]["validation"], audit_seed=audit_seed, output=str(output)), allow_nan=False))


if __name__ == "__main__":
    main()
