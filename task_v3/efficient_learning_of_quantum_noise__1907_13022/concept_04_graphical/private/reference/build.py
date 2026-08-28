import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from author_tools import case, oracle, save_model
from solver import learn
from weak_solver import solve as weak_solve


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ("mediated_chain", "loop_ladder", "branch_triples")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(seed, region):
    reference = ROOT / "private/reference"
    for directory in (reference / "core/inputs", reference / "core/truth", reference / "challenge_truth", reference / "models", ROOT / "private/challenge_pool"):
        directory.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "seed": seed, "region": region, "cases": [], "generator_sha256": digest(Path(__file__)), "author_tools_sha256": digest(reference / "author_tools.py")}
    sizes = {
        "core": ((96, 100, 104), (96, 100, 104), (96, 102, 108)),
        "challenge": ((108, 112), (108, 112), (99, 111)),
    }
    for pool_index, pool in enumerate(("core", "challenge")):
        for family_index, family in enumerate(FAMILIES):
            for instance, num_variables in enumerate(sizes[pool][family_index]):
                ordinal = family_index * len(sizes[pool][family_index]) + instance + 1
                identifier = ("c" if pool == "core" else "h") + f"{ordinal:02d}"
                stream = np.random.SeedSequence([seed, region, pool_index, family_index, instance, 74021])
                started = time.monotonic()
                data, coefficients, order = case(family, num_variables, stream, region, pool == "challenge")
                reconstructed = learn(data)
                keys = set(coefficients) | set(reconstructed)
                coefficient_error = max(abs(coefficients.get(scope, 0.0) - reconstructed.get(scope, 0.0)) for scope in keys)
                if coefficient_error > 1e-6:
                    raise AssertionError(f"Recovery mismatch: {identifier}: {coefficient_error}")
                target = oracle(data, coefficients, order)
                baseline = weak_solve(data)
                if not np.all(np.isfinite(target)) or np.any(target >= 0):
                    raise AssertionError("Invalid oracle probabilities")
                baseline_gap = np.abs(baseline - target)
                if np.min(baseline_gap) < 0.15:
                    raise AssertionError(f"Insufficient baseline separation: {identifier}: {np.min(baseline_gap)}")
                input_path = reference / "core/inputs" / f"{identifier}.npz" if pool == "core" else ROOT / "private/challenge_pool" / f"{identifier}.npz"
                truth_path = reference / ("core/truth" if pool == "core" else "challenge_truth") / f"{identifier}.npz"
                model_path = reference / "models" / f"{identifier}.npz"
                np.savez_compressed(input_path, **data)
                np.savez_compressed(truth_path, target=target, baseline=baseline, event_group=data["event_group"])
                save_model(model_path, coefficients, order)
                entry = {
                    "id": identifier, "family": family, "pool": pool, "n": num_variables, "queries": len(target),
                    "input": str(input_path.relative_to(ROOT)), "truth": str(truth_path.relative_to(ROOT)),
                    "model": str(model_path.relative_to(ROOT)), "input_sha256": digest(input_path),
                    "truth_sha256": digest(truth_path), "coefficient_max_error": coefficient_error,
                    "min_baseline_log_gap": float(np.min(baseline_gap)), "min_log_event": float(np.min(target)),
                    "max_log_event": float(np.max(target)), "author_seconds": time.monotonic() - started,
                }
                manifest["cases"].append(entry)
                print(f"{identifier} {family} n={num_variables} recovery={coefficient_error:.2g} gap={np.min(baseline_gap):.3g} logmin={np.min(target):.1f} seconds={entry['author_seconds']:.2f}", flush=True)
    example, coefficients, order = case("branch_triples", 9, np.random.SeedSequence([seed, region, 55581]))
    selection = np.asarray([0, 6, 12, 17])
    for key in ("log_activity", "fixed", "count_mask", "weight_lo", "weight_hi", "parity_mask", "parity_value", "event_group"):
        example[key] = example[key][selection]
    sample_path = ROOT / "participant/input/example.npz"
    np.savez_compressed(sample_path, **example)
    manifest["example_sha256"] = digest(sample_path)
    (reference / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--region", type=int, choices=(0, 1, 2), default=0)
    arguments = parser.parse_args()
    build(arguments.seed, arguments.region)
