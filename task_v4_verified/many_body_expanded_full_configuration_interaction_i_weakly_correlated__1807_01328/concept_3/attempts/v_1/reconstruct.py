"""Recover pair Hamiltonians from public low-order CAS data."""

import argparse
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigvals, eigh
from scipy.optimize import brentq


DEFAULT_ASSETS = Path(
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/"
    "many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/"
    "concept_3/participant/input/workspace"
)


def load_generator(assets):
    specification = importlib.util.spec_from_file_location(
        "public_pair_generator", assets / "generator.py"
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def load_archive(path):
    with np.load(path, allow_pickle=False) as archive:
        return dict(archive)


def lowest(matrix):
    return float(eigh(matrix, subset_by_index=(0, 0), eigvals_only=True,
                      check_finite=False, driver="evr")[0])


def transfer_operator(generator, n_pairs, n_virtual, left, right):
    occupancy, edges = generator.basis(n_pairs + n_virtual, n_pairs)
    rows, columns, sources, destinations = edges
    selected = (((sources == n_pairs + left) & (destinations == n_pairs + right)) |
                ((sources == n_pairs + right) & (destinations == n_pairs + left)))
    result = np.zeros((len(occupancy), len(occupancy)))
    result[rows[selected], columns[selected]] = 1.0
    result[columns[selected], rows[selected]] = 1.0
    return result


def infer_pair_candidates(base, operator, energy, sign, bound):
    shifted = energy * np.eye(len(base)) - base
    roots = eigvals(shifted, operator, check_finite=False)
    candidates = []
    for root in roots:
        if not np.isfinite(root) or abs(root.imag) > 1e-8:
            continue
        transfer = float(root.real)
        magnitude = sign * transfer
        if magnitude < 0.012 - 1e-8 or magnitude > bound + 1e-8:
            continue
        transfer = sign * np.clip(magnitude, 0.012, bound)
        if abs(lowest(base + transfer * operator) - energy) > 2e-10:
            continue
        if not any(abs(transfer - previous) < 1e-9 for previous in candidates):
            candidates.append(float(transfer))
    if not candidates:
        grid = np.linspace(0.012, bound, 257)
        residuals = [lowest(base + sign * magnitude * operator) - energy
                     for magnitude in grid]
        for index, magnitude in enumerate(grid):
            if abs(residuals[index]) < 1e-13:
                candidates.append(float(sign * magnitude))
            if index and residuals[index - 1] * residuals[index] < 0.0:
                root = brentq(
                    lambda value: lowest(base + sign * value * operator) - energy,
                    grid[index - 1], magnitude, xtol=5e-15, rtol=1e-14,
                )
                candidates.append(float(sign * root))
    if not candidates:
        raise RuntimeError("No physical transfer matches a supplied pair CAS energy")
    return sorted(candidates, key=abs)


def reconstruct(features, generator):
    n_pairs = int(features["n_pairs"])
    n_virtual = int(features["n_virtual"])
    size = n_pairs + n_virtual
    profile = np.asarray(features["occupied_profile"][:n_pairs])
    singleton = np.asarray(features["cas1"][:n_virtual])
    gaps = np.asarray(features["diagonal_gaps"][:n_pairs, :n_virtual])
    denominator = np.sum(profile[:, None] ** 2 / (gaps - singleton[None, :]), axis=0)
    amplitudes = np.sqrt(-singleton / denominator)
    if not np.all(np.isfinite(amplitudes)):
        raise RuntimeError("Invalid singleton inversion")
    hopping = np.zeros((size, size))
    hopping[:n_pairs, n_pairs:] = -profile[:, None] * amplitudes[None, :]
    hopping[n_pairs:, :n_pairs] = hopping[:n_pairs, n_pairs:].T
    model = generator.Hamiltonian(
        n_pairs, n_virtual, int(features["family"]),
        np.asarray(features["onsite"][:size]),
        np.asarray(features["density"][:size, :size]), hopping, profile,
        np.asarray(features["positions"][:n_virtual]),
        np.asarray(features["groups"][:n_virtual]),
    )
    reference = float(features["reference_energy"])
    operator = transfer_operator(generator, n_pairs, 2, 0, 1)
    candidates = {}
    pair_targets = {}
    for slot, pair_array in enumerate(generator.PAIR_INDEX):
        left, right = (int(value) for value in pair_array)
        if right >= n_virtual:
            continue
        pair = (left, right)
        base = generator.matrix(model, pair)
        target = reference + float(features["cas2"][slot])
        sign = int(features["pair_sign"][slot])
        candidates[pair] = infer_pair_candidates(base, operator, target, sign,
                                                 generator.EDGE_BOUND)
        pair_targets[pair] = target
    ambiguous = {pair: values for pair, values in candidates.items() if len(values) > 1}
    choices = {pair: 0 for pair in candidates}
    if ambiguous:
        costs = {pair: np.zeros(len(values)) for pair, values in ambiguous.items()}
        for slot, triple_array in enumerate(generator.TRIPLE_INDEX):
            triple = tuple(int(value) for value in triple_array)
            if triple[-1] >= n_virtual:
                continue
            pairs = list(itertools.combinations(triple, 2))
            if not any(pair in ambiguous for pair in pairs):
                continue
            base = generator.matrix(model, triple)
            operators = [transfer_operator(generator, n_pairs, 3,
                                            triple.index(pair[0]), triple.index(pair[1]))
                         for pair in pairs]
            target = reference + float(features["cas3"][slot])
            local_costs = {pair: np.full(len(candidates[pair]), np.inf)
                           for pair in pairs if pair in ambiguous}
            for indices in itertools.product(*(range(len(candidates[pair])) for pair in pairs)):
                matrix = base.copy()
                for pair, index, edge_operator in zip(pairs, indices, operators):
                    matrix += candidates[pair][index] * edge_operator
                error_squared = (lowest(matrix) - target) ** 2
                for pair, index in zip(pairs, indices):
                    if pair in local_costs:
                        local_costs[pair][index] = min(local_costs[pair][index], error_squared)
            for pair in local_costs:
                costs[pair] += local_costs[pair]
        for pair in ambiguous:
            choices[pair] = int(np.argmin(costs[pair]))
    for (left, right), values in candidates.items():
        hopping[n_pairs + left, n_pairs + right] = values[choices[(left, right)]]
        hopping[n_pairs + right, n_pairs + left] = values[choices[(left, right)]]
    singleton_error = max(abs(generator.ground(model, (virtual,)) - reference - singleton[virtual])
                          for virtual in range(n_virtual))
    pair_error = max(abs(generator.ground(model, pair) - target)
                     for pair, target in pair_targets.items())
    triple_error = 0.0
    for slot, triple_array in enumerate(generator.TRIPLE_INDEX):
        triple = tuple(int(value) for value in triple_array)
        if triple[-1] < n_virtual:
            residual = generator.ground(model, triple) - reference - features["cas3"][slot]
            triple_error = max(triple_error, abs(float(residual)))
    if max(singleton_error, pair_error, triple_error) > 1e-9:
        raise RuntimeError(f"Low-order reconstruction failed: {singleton_error}, "
                           f"{pair_error}, {triple_error}")
    energy, reference_weight, eigen_residual = generator.ground(model, vectors=True)
    tail = energy - reference - float(features["truncated_correlation"])
    diagnostics = {
        "singleton_max_residual": float(singleton_error),
        "pair_max_residual": float(pair_error),
        "triple_max_residual": float(triple_error),
        "full_eigen_residual": float(eigen_residual),
        "reference_weight": float(reference_weight),
        "ambiguous_pairs": len(ambiguous),
        "minimum_amplitude": float(amplitudes.min()),
        "maximum_amplitude": float(amplitudes.max()),
    }
    return float(tail), diagnostics, model


def metrics(target, prediction, families):
    errors = prediction - target
    family_rmse = {
        str(int(family)): float(np.sqrt(np.mean(errors[families == family] ** 2)))
        for family in np.unique(families)
    }
    return {
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "worst_family_rmse": max(family_rmse.values()),
        "family_rmse": family_rmse,
        "maximum_absolute_error": float(np.max(np.abs(errors))),
    }


def predict_split(data, generator, split):
    predictions = []
    diagnostics = []
    started = time.perf_counter()
    feature_keys = [key for key in data if key not in ("ids", "tail")]
    for row in range(len(data["ids"])):
        features = {key: data[key][row] for key in feature_keys}
        prediction, diagnostic, _ = reconstruct(features, generator)
        predictions.append(prediction)
        diagnostics.append(diagnostic)
        if (row + 1) % 64 == 0 or row + 1 == len(data["ids"]):
            print(f"{split}: {row + 1}/{len(data['ids'])}, "
                  f"{time.perf_counter() - started:.2f}s", flush=True)
    predictions = np.asarray(predictions, dtype=np.float64)
    report = {
        "rows": len(predictions),
        "runtime_seconds": time.perf_counter() - started,
        "max_singleton_residual": max(item["singleton_max_residual"] for item in diagnostics),
        "max_pair_residual": max(item["pair_max_residual"] for item in diagnostics),
        "max_triple_residual": max(item["triple_max_residual"] for item in diagnostics),
        "max_full_eigen_residual": max(item["full_eigen_residual"] for item in diagnostics),
        "minimum_reference_weight": min(item["reference_weight"] for item in diagnostics),
        "ambiguous_pairs": sum(item["ambiguous_pairs"] for item in diagnostics),
    }
    if "tail" in data:
        report["metrics"] = metrics(data["tail"], predictions, data["family"])
    return predictions, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output-directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--splits", nargs="+", default=["validation", "train", "test_features"])
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    generator = load_generator(args.assets)
    report = {"method": "exact low-order Hamiltonian inversion", "splits": {}}
    for split in args.splits:
        data = load_archive(args.assets / "data" / f"{split}.npz")
        predictions, split_report = predict_split(data, generator, split)
        filename = "predictions.npz" if split == "test_features" else f"{split}_predictions.npz"
        np.savez_compressed(args.output_directory / filename,
                            ids=data["ids"].astype("U32"), tail=predictions)
        report["splits"][split] = split_report
        (args.output_directory / "reconstruction_report.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(json.dumps({split: split_report}), flush=True)


if __name__ == "__main__":
    main()
