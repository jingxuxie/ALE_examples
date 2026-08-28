"""Private, bounded longer-range search using unchanged official observations."""

import argparse
import gc
import importlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parent
PILOT = PRIVATE.parent
TARGET = PILOT.parents[1]
sys.path.insert(0, str(HERE))
import build as original

import numpy as np
from symfc import Symfc
from symfc.solvers import FCSolverO2, FCSolverO3, FCSolverO2O3
from physics import fold_harmonic, harmonic_forces, invariant_errors, load_npz, mixed_forces, validate_output

SEARCH = [
    {"name": "nacl64_full", "original": "initial_nacl_64_512", "cutoff": None, "short_cutoff": 4.5},
    {"name": "gan128_r55", "original": "heldout_gan_128", "cutoff": 5.5, "short_cutoff": 4.0},
    {"name": "sno272_r55", "original": "heldout_sno2_72", "cutoff": 5.5, "short_cutoff": 4.0},
]


def rmse(values):
    return float(np.sqrt(np.mean(np.asarray(values) ** 2))) if np.size(values) else 0.0


def full_harmonic_forces(tensor, displacements):
    return -np.einsum("ijab,sjb->sia", tensor, displacements, optimize=True)


def full_cubic_forces(tensor, displacements):
    result = np.zeros_like(displacements)
    flattened = displacements.reshape(len(displacements), -1)
    for atom, block in enumerate(tensor):
        matrices = block.transpose(2, 0, 3, 1, 4).reshape(3, flattened.shape[1], flattened.shape[1])
        for axis, matrix in enumerate(matrices):
            result[:, atom, axis] = -0.5 * np.sum((flattened @ matrix) * flattened, axis=1)
    return result


def native_fold(full_fc2, atoms2, atoms3):
    large_to_small = original.match_atoms(
        atoms2.scaled_positions @ atoms2.cell @ np.linalg.inv(atoms3.cell),
        atoms3.scaled_positions, atoms2.numbers, atoms3.numbers,
    )
    small_to_large = original.match_atoms(
        atoms3.scaled_positions @ atoms3.cell @ np.linalg.inv(atoms2.cell),
        atoms2.scaled_positions, atoms3.numbers, atoms2.numbers,
    )
    folded = np.zeros((len(atoms3), len(atoms3), 3, 3))
    for atom, large_atom in enumerate(small_to_large):
        np.add.at(folded[atom], large_to_small, full_fc2[large_atom])
    return folded


def objective_gradient(bases, orders, residual, displacements, data, suffix):
    atom_count = len(data["s2p" + suffix])
    representative_count = len(data["p2s" + suffix])
    inverse_maps = np.argsort(data["compact_map" + suffix], axis=1)
    gradients = {}
    for order in orders:
        gradients[order] = np.zeros((representative_count,) + (atom_count,) * (order - 1) + (3,) * order)
    for atom in range(atom_count):
        representative = data["s2p" + suffix][atom]
        shifted = displacements[:, inverse_maps[atom], :]
        if 2 in orders:
            gradients[2][representative] -= np.einsum("sa,sjb->jab", residual[:, atom], shifted)
        if 3 in orders:
            gradients[3][representative] -= 0.5 * np.einsum(
                "sa,sjb,skc->jkabc", residual[:, atom], shifted, shifted, optimize=True,
            )
    projected = []
    for order in orders:
        basis = bases[order]
        compressed = basis.compact_compression_matrix.T @ gradients[order].reshape(-1)
        projected.append(basis.blocked_basis_set.transpose_dot(compressed))
    return np.concatenate(projected)


def fit_native(atoms, displacements, forces, orders, cutoff, data, suffix):
    started = time.perf_counter()
    context = Symfc(atoms, cutoff={3: cutoff}, log_level=0)
    context.compute_basis_set(orders=orders)
    if not np.array_equal(context.p2s_map, data["p2s" + suffix]):
        raise ValueError("Native and public primitive representatives differ")
    dimensions = {str(order): int(context.basis_set[order].basis_set.shape[1]) for order in orders}
    label = "O2O3" if orders == [2, 3] else "O" + str(orders[0])
    module = importlib.import_module("symfc.solvers.solver_" + label)
    preparation_name = "prepare_normal_equation_" + label
    preparation = getattr(module, preparation_name)
    captured = {}

    def capture(*arguments, **keywords):
        normal, right = preparation(*arguments, **keywords)
        captured["normal"] = normal.copy()
        captured["right"] = right.copy()
        return normal, right

    setattr(module, preparation_name, capture)
    try:
        if orders == [2, 3]:
            solver = FCSolverO2O3([context.basis_set[2], context.basis_set[3]])
        elif orders == [2]:
            solver = FCSolverO2(context.basis_set[2])
        else:
            solver = FCSolverO3(context.basis_set[3])
        solver.solve(np.ascontiguousarray(displacements), np.ascontiguousarray(forces))
    finally:
        setattr(module, preparation_name, preparation)
    fit_seconds = time.perf_counter() - started
    compact_values = solver.compact_fc if len(orders) == 2 else (solver.compact_fc,)
    full_values = solver.full_fc if len(orders) == 2 else (solver.full_fc,)
    compact = {"fc" + str(order): value for order, value in zip(orders, compact_values)}
    full = dict(zip(orders, full_values))
    prediction = np.zeros_like(forces)
    if 2 in full:
        prediction += full_harmonic_forces(full[2], displacements)
    if 3 in full:
        prediction += full_cubic_forces(full[3], displacements)
    residual = prediction - forces
    coefficients = np.concatenate(solver.coefs) if len(orders) == 2 else solver.coefs
    normal, right = captured["normal"], captured["right"]
    eigenvalues = np.linalg.eigvalsh(normal)
    rank_tolerance = float(eigenvalues[-1]) * len(eigenvalues) * np.finfo(float).eps * 64
    normal_rank = int(np.count_nonzero(eigenvalues > rank_tolerance))
    scale = max(float(np.linalg.norm(right)), 1e-30)
    normal_gradient = float(np.linalg.norm(normal @ coefficients - right) / scale)
    direct_gradient = float(np.linalg.norm(objective_gradient(context.basis_set, orders, residual, displacements, data, suffix)) / scale)
    predicted_sse = float(np.sum(forces ** 2) - 2 * coefficients @ right + coefficients @ normal @ coefficients)
    direct_sse = float(np.sum(residual ** 2))
    sse_disagreement = abs(predicted_sse - direct_sse) / max(float(np.sum(forces ** 2)), 1e-30)
    audit = {
        "orders": orders, "basis_dimensions": dimensions, "fit_seconds": fit_seconds,
        "audit_seconds": time.perf_counter() - started - fit_seconds,
        "native_training_rmse": rmse(residual), "direct_training_sse": direct_sse,
        "normal_equation_training_sse": predicted_sse,
        "normal_equation_relative_gradient": normal_gradient,
        "direct_force_relative_gradient": direct_gradient,
        "relative_sse_disagreement": sse_disagreement,
        "parameter_count": len(coefficients), "normal_numerical_rank": normal_rank,
        "normal_rank_tolerance": rank_tolerance,
        "normal_minimum_eigenvalue": float(eigenvalues[0]),
        "normal_maximum_eigenvalue": float(eigenvalues[-1]),
        "design_condition_estimate": float(np.sqrt(eigenvalues[-1] / eigenvalues[0])) if eigenvalues[0] > 0 else None,
        "rank_certificate": "full_rank_well_above_normal_roundoff" if normal_rank == len(coefficients) else "rank_uncertain_requires_direct_design_or_sparse_solver",
    }
    if max(normal_gradient, direct_gradient, sse_disagreement) > 1e-7:
        raise ValueError("Invalid native objective audit: " + json.dumps(audit))
    return compact, full, audit


def build_worker(search, seed):
    started = time.perf_counter()
    configuration = dict(next(item for item in original.CASES if item["id"] == search["original"]))
    identifier = "ce_" + search["name"] + "_s" + str(seed)
    folder = PRIVATE / "challenge_pool" / identifier
    artifacts = HERE / "counterexamples" / identifier
    folder.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    atoms2, atoms3, all_u2, all_f2, all_u3, all_f3 = original.load_source(configuration)
    generator = np.random.default_rng(np.random.SeedSequence([seed, SEARCH.index(search), 741]))
    indices3 = generator.permutation(len(all_u3))
    train3 = indices3[:configuration["train3"]]
    test3 = indices3[configuration["train3"]:configuration["train3"] + configuration["test3"]]
    indices2 = generator.permutation(len(all_u2))
    train2 = indices2[:configuration.get("train2", 0)]
    test2 = indices2[configuration.get("train2", 0):]
    cutoff = search["cutoff"]
    if cutoff is None:
        cutoff = float(np.linalg.norm(atoms3.cell, axis=1).sum() / 2 + 1e-6)
    data = {
        "schema_version": np.asarray(1, dtype=np.int64),
        "fit_mode": np.asarray(configuration["mode"], dtype=np.int64),
        "cutoff3": np.asarray(cutoff), "u2": all_u2[train2], "f2": all_f2[train2],
        "u3": all_u3[train3], "f3": all_f3[train3],
    }
    data.update(original.geometry(atoms2, "2"))
    data.update(original.geometry(atoms3, "3"))
    data["fold2to3"] = original.folding_map(data)
    data["triplet_mask3"] = original.support_mask(atoms3, data["p2s3"], cutoff)
    if search["cutoff"] is None and not np.all(data["triplet_mask3"]):
        raise ValueError("Full-range case is not full")
    input_path = folder / "input.npz"
    np.savez_compressed(input_path, **data)
    audits = []
    if configuration["mode"] == 1:
        result, native2, audit = fit_native(atoms2, data["u2"], data["f2"], [2], cutoff, data, "2")
        audits.append(audit)
        folded_native = native_fold(native2[2], atoms2, atoms3)
        residual = data["f3"] - full_harmonic_forces(folded_native, data["u3"])
        cubic, native3, audit = fit_native(atoms3, data["u3"], residual, [3], cutoff, data, "3")
        audits.append(audit)
        result.update(cubic)
        native3[2] = folded_native
        short, short_native, short_audit = fit_native(atoms3, data["u3"], residual, [3], search["short_cutoff"], data, "3")
        short["fc2"] = result["fc2"]
        short_native[2] = folded_native
    else:
        result, native3, audit = fit_native(atoms3, data["u3"], data["f3"], [2, 3], cutoff, data, "3")
        audits.append(audit)
        native2 = {2: native3[2]}
        short, short_native, short_audit = fit_native(atoms3, data["u3"], data["f3"], [2, 3], search["short_cutoff"], data, "3")
    validate_output(result, data)
    invariants = invariant_errors(result, data)
    native_train = full_harmonic_forces(native3[2], data["u3"]) + full_cubic_forces(native3[3], data["u3"])
    native_test = full_harmonic_forces(native3[2], all_u3[test3]) + full_cubic_forces(native3[3], all_u3[test3])
    short_test = full_harmonic_forces(short_native[2], all_u3[test3]) + full_cubic_forces(short_native[3], all_u3[test3])
    compact_disagreement = max(
        float(np.max(np.abs(native_train - mixed_forces(result, data["u3"], data)))),
        float(np.max(np.abs(native_test - mixed_forces(result, all_u3[test3], data)))),
    )
    if max(invariants.values()) > 1e-6 or compact_disagreement > 1e-8:
        raise ValueError("Reference invariant/contraction audit failed")
    reference = dict(result)
    reference.update(heldout_u2=all_u2[test2], heldout_f2=all_f2[test2], heldout_u3=all_u3[test3], heldout_f3=all_f3[test3])
    reference_path = artifacts / "reference.npz"
    np.savez_compressed(reference_path, **reference)
    np.savez_compressed(artifacts / "short_range_reference.npz", **short)
    np.savez_compressed(artifacts / "native_predictions.npz", train3=native_train, heldout3=native_test,
                        heldout2=full_harmonic_forces(native2[2], all_u2[test2]) if len(test2) else np.empty_like(all_u2),
                        short_heldout3=short_test)
    short_mask = original.support_mask(atoms3, data["p2s3"], search["short_cutoff"])
    long_norm_fraction = float(np.linalg.norm(result["fc3"][~short_mask]) / max(np.linalg.norm(result["fc3"]), 1e-30))
    source_files = [configuration["source"]] + (["symfc/tests/conftest.py"] if "fixture" in configuration else [])
    provenance = json.loads((HERE / "provenance.json").read_text())
    sources = []
    for source in source_files:
        repository, relative = source.split("/", 1)
        organization = "symfc" if repository == "symfc" else "phonopy"
        commit = provenance["source_commits"][repository]
        sources.append({"path": source, "sha256": original.sha256(original.SOURCES / source),
                        "url": f"https://github.com/{organization}/{repository}/blob/{commit}/{relative}"})
    metadata = {
        "id": identifier, "family": configuration["family"], "split": "counterexample_search",
        "input": str(input_path.relative_to(PRIVATE)), "reference": str(reference_path.relative_to(PRIVATE)),
        "baseline": str((artifacts / "baseline/result.npz").relative_to(PRIVATE)),
        "timeout": 180, "memory_mb": 8192, "keys": ["fc2", "fc3"], "core": True,
        "seed": seed, "source_case": search["original"], "sources": sources,
        "n2": len(atoms2), "n3": len(atoms3), "fit_mode": configuration["mode"],
        "cutoff3_angstrom": cutoff, "full_range": search["cutoff"] is None,
        "short_cutoff3_angstrom": search["short_cutoff"],
        "train2_indices": train2.tolist(), "test2_indices": test2.tolist(),
        "train3_indices": train3.tolist(), "test3_indices": test3.tolist(),
        "basis_dimensions_private": {key: value for audit in audits for key, value in audit["basis_dimensions"].items()},
        "runtime_versions": provenance["runtime_versions"], "oracle_tag_commit": provenance["oracle_tag_commit"],
        "native_audits": audits, "short_range_audit": short_audit,
        "native_compact_max_abs_difference": compact_disagreement, "invariant_errors": invariants,
        "training_force3_rmse": rmse(native_train - data["f3"]),
        "heldout_force3_rmse": rmse(native_test - all_f3[test3]),
        "short_range_heldout_force3_rmse": rmse(short_test - all_f3[test3]),
        "outside_short_cutoff_fc3_norm_fraction": long_norm_fraction,
        "reference_validated": True, "worker_seconds": time.perf_counter() - started,
        "worker_max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    metadata["files"] = {key: metadata[key] for key in ("input", "reference", "baseline")}
    original.dump_json(folder / "metadata.json", metadata)
    print(json.dumps({key: metadata[key] for key in ("id", "basis_dimensions_private", "worker_seconds", "worker_max_rss_kb", "heldout_force3_rmse", "short_range_heldout_force3_rmse")}), flush=True)


def bounded_reference(search, seed):
    identifier = "ce_" + search["name"] + "_s" + str(seed)
    artifacts = HERE / "counterexamples" / identifier
    artifacts.mkdir(parents=True, exist_ok=True)
    command = ["/usr/bin/time", "-f", "%M", "-o", str(artifacts / "reference.resources.txt"),
               sys.executable, "-B", str(Path(__file__).resolve()), "--worker", search["name"], "--seed", str(seed)]

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (8192 * 1024 ** 2,) * 2)

    started = time.perf_counter()
    with (artifacts / "reference.stdout.txt").open("w") as stdout, (artifacts / "reference.stderr.txt").open("w") as stderr:
        child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=limits)
        status = "ok"
        try:
            child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            status = "timeout"
        if child.returncode and status == "ok":
            status = "error"
    measurements = {"status": status, "seconds": time.perf_counter() - started, "returncode": child.returncode,
                    "timeout": 180, "memory_mb": 8192, "memory_limit_kind": "RLIMIT_AS"}
    resource_path = artifacts / "reference.resources.txt"
    resource_lines = resource_path.read_text().splitlines() if resource_path.exists() else []
    measurements["max_rss_kb"] = int(resource_lines[-1]) if resource_lines and resource_lines[-1].isdigit() else None
    original.dump_json(artifacts / "reference_run.json", measurements)
    return measurements


def run_comparison(case, reference_run):
    sys.path.insert(0, str(PRIVATE))
    evaluator = importlib.import_module("evaluator")
    runner = evaluator.load_common_runner()
    artifacts = HERE / "counterexamples" / case["id"]
    solver = PILOT / "attempt/solve.py"
    before = original.sha256(solver)
    reference = load_npz(PRIVATE / case["reference"])
    data = load_npz(PRIVATE / case["input"])
    native = load_npz(artifacts / "native_predictions.npz")
    run = runner(solver, PRIVATE / case["input"], artifacts / "model", PILOT / "participant", timeout=180, memory_mb=8192)
    original.dump_json(artifacts / "model_run.json", run)
    baseline_run = runner(PILOT / "participant/workspace/solve.py", PRIVATE / case["input"], artifacts / "baseline", PILOT / "participant", timeout=180, memory_mb=8192)
    original.dump_json(artifacts / "baseline_run.json", baseline_run)
    result = {"id": case["id"], "reference_run": reference_run, "model_run": run,
              "baseline_run": baseline_run, "solver_sha256": before, "reference_validated": True}
    if original.sha256(solver) != before:
        raise ValueError("Submission changed during comparison")
    if baseline_run["status"] == "ok":
        baseline = load_npz(Path(baseline_run["output_path"]))
        zero = {key: np.zeros_like(reference[key]) for key in ("fc2", "fc3")}
        result["unchanged_score_zero"] = evaluator.score_details(zero, reference, baseline, case, data)
        result["unchanged_score_reference"] = evaluator.score_details(reference, reference, baseline, case, data)
        if run["status"] == "ok":
            actual = load_npz(Path(run["output_path"]))
            result["unchanged_score_model"] = evaluator.score_details(actual, reference, baseline, case, data)
    if run["status"] == "ok":
        actual = load_npz(Path(run["output_path"]))
        validate_output(actual, data)
        prediction = mixed_forces(actual, data["u3"], data)
        heldout = mixed_forces(actual, reference["heldout_u3"], data)
        raw = {"fc2_relative_error": float(np.linalg.norm(actual["fc2"] - reference["fc2"]) / np.linalg.norm(reference["fc2"])),
               "fc3_relative_error": float(np.linalg.norm(actual["fc3"] - reference["fc3"]) / np.linalg.norm(reference["fc3"])),
               "model_training_force3_rmse": rmse(prediction - data["f3"]),
               "reference_training_force3_rmse": rmse(native["train3"] - data["f3"]),
               "model_heldout_force3_rmse": rmse(heldout - reference["heldout_f3"]),
               "reference_heldout_force3_rmse": rmse(native["heldout3"] - reference["heldout_f3"]),
               "training_prediction_reference_rmse": rmse(prediction - native["train3"]),
               "heldout_prediction_reference_rmse": rmse(heldout - native["heldout3"])}
        if len(data["u2"]):
            prediction2 = harmonic_forces(actual["fc2"], data["u2"], data["s2p2"], data["compact_map2"])
            heldout2 = harmonic_forces(actual["fc2"], reference["heldout_u2"], data["s2p2"], data["compact_map2"])
            raw.update(model_training_force2_rmse=rmse(prediction2 - data["f2"]),
                       model_heldout_force2_rmse=rmse(heldout2 - reference["heldout_f2"]),
                       reference_heldout_force2_rmse=rmse(native["heldout2"] - reference["heldout_f2"]))
        raw.update(invariant_errors(actual, data))
        result["raw_metrics"] = raw
        if raw["model_training_force3_rmse"] + 1e-7 < raw["reference_training_force3_rmse"]:
            result["interpretation"] = "invalid_or_misaligned_reference_do_not_count"
        elif max(raw["fc2_relative_error"], raw["fc3_relative_error"]) < 1e-5:
            result["interpretation"] = "solver_matches_reference_no_counterexample"
        elif raw["training_prediction_reference_rmse"] < 1e-7:
            result["interpretation"] = "possible_nonidentifiability_not_a_demonstrated_failure"
        else:
            result["interpretation"] = "candidate_numerical_failure_requires_review"
    else:
        result["interpretation"] = "candidate_runtime_failure_requires_review"
    original.dump_json(artifacts / "comparison.json", result)
    print(json.dumps({"id": case["id"], "model_status": run["status"], "model_seconds": run["seconds"],
                      "interpretation": result["interpretation"], "raw_metrics": result.get("raw_metrics")}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=9082716)
    parser.add_argument("--case", action="append", choices=[item["name"] for item in SEARCH])
    parser.add_argument("--worker", choices=[item["name"] for item in SEARCH])
    parser.add_argument("--compare-only", action="store_true")
    parser.add_argument("--reference-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.worker:
        build_worker(next(item for item in SEARCH if item["name"] == arguments.worker), arguments.seed)
        return
    manifest = []
    comparisons = []
    for search in SEARCH:
        if arguments.case and search["name"] not in arguments.case:
            continue
        identifier = "ce_" + search["name"] + "_s" + str(arguments.seed)
        artifact_path = HERE / "counterexamples" / identifier
        reference_run = json.loads((artifact_path / "reference_run.json").read_text()) if arguments.compare_only else bounded_reference(search, arguments.seed)
        if reference_run["status"] != "ok":
            comparisons.append({"id": identifier, "reference_run": reference_run, "interpretation": "reference_failed_ineligible_as_counterexample"})
            print(json.dumps(comparisons[-1]), flush=True)
            continue
        metadata = json.loads((PRIVATE / "challenge_pool" / identifier / "metadata.json").read_text())
        metadata["reference_run"] = reference_run
        manifest.append(metadata)
        original.dump_json(PRIVATE / "challenge_pool/counterexamples_manifest.json", manifest)
        if arguments.reference_only:
            comparison = json.loads((artifact_path / "comparison.json").read_text())
            comparison.setdefault("first_reference_run", comparison["reference_run"])
            comparison["reference_run"] = reference_run
            original.dump_json(artifact_path / "comparison.json", comparison)
            comparisons.append(comparison)
            print(json.dumps({"id": identifier, "reference_run": reference_run,
                              "ranks": [{key: audit[key] for key in ("orders", "normal_numerical_rank", "parameter_count", "design_condition_estimate", "rank_certificate")} for audit in metadata["native_audits"]]}), flush=True)
        else:
            comparisons.append(run_comparison(metadata, reference_run))
        original.dump_json(HERE / "counterexamples/search_results.json", comparisons)
        gc.collect()
    original.dump_json(PRIVATE / "challenge_pool/counterexamples_manifest.json", manifest)
    original.dump_json(HERE / "counterexamples/search_results.json", comparisons)


if __name__ == "__main__":
    main()
