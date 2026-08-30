import argparse
import hashlib
import importlib.util
import json
import math
import os
import resource
import sys
import time
from collections import defaultdict
from pathlib import Path


for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
bootstrap = argparse.ArgumentParser(add_help=False)
bootstrap.add_argument("--cpu", type=int, default=187)
bootstrap_arguments, _ = bootstrap.parse_known_args()
if bootstrap_arguments.cpu == 188 or bootstrap_arguments.cpu not in os.sched_getaffinity(0):
    raise ValueError("Private CPU must be allowed and must not be CPU 188")
os.sched_setaffinity(0, {bootstrap_arguments.cpu})

import numpy as np
from scipy.linalg import block_diag, expm


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
FROZEN = ROOT / "generations/generation_1"
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import validate_solution


def module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


GENERATOR = module("trusted_second_pool_generator", "adversary/generate.py")
PORTFOLIO = module("trusted_second_pool_optimizer", "adversary/portfolio/solver.py")
BASELINE = module("trusted_second_pool_spectral_scaling", "participant/baseline/solver.py")


def write_json(name, value):
    path = DIRECTORY / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False))
    temporary.replace(path)


def witness(identifier, orbital, auxiliary):
    return {"id": identifier, "orbital": orbital.tolist(), "auxiliary": auxiliary.tolist()}


def spectrum(case):
    factors = np.asarray(case["factors"])
    matrix = np.asarray(case["one_body"]) + 0.5 * np.einsum("aij,ajk->ik", factors, factors)
    return np.linalg.eigvalsh(matrix)


def polar(matrix):
    left, _, right = np.linalg.svd(matrix)
    return left @ right


def source_snapshot():
    manifest = json.loads((FROZEN / "freeze_manifest.json").read_text())
    snapshot = {str((FROZEN / name).relative_to(ROOT)): hashlib.sha256((FROZEN / name).read_bytes()).hexdigest() for name in manifest}
    for relative in ("adversary/generate.py", "adversary/portfolio/solver.py", "participant/baseline/solver.py", "evaluator/evaluate.py"):
        snapshot[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    mismatches = [name for name, expected in manifest.items() if snapshot[str((FROZEN / name).relative_to(ROOT))] != expected]
    return snapshot, mismatches


def make_pool():
    cases, inputs, proofs, starts = [], [], [], {}
    regimes = (("secondary_weaker", 0.75, 0.90), ("balanced", 0.90, 1.10), ("secondary_stronger", 1.10, 1.35))
    public_cases = json.loads((FROZEN / "participant/input/examples.json").read_text())["cases"]
    prior = json.loads((ROOT / "adversary/competing_search/provenance.json").read_text())["cases"]
    prior_seeds = {seed for record in prior for seed in record["parent_seeds"]}
    public_spectra = {case["id"]: spectrum(case) for case in public_cases}
    for dimension in (14, 16):
        for regime_index, (regime, lower, upper) in enumerate(regimes):
            for replicate in range(4):
                index = len(cases)
                seed = 82940821 + 10007 * index
                generator = np.random.default_rng(seed)
                rank = dimension - 2
                first_rank = rank // 2
                identifier = f"second_pool_{index + 1:03d}"
                parent_seeds = [seed + 17, seed + 53]
                if prior_seeds.intersection(parent_seeds):
                    raise ValueError("Parent seed overlaps a prior case")
                first, first_witness, _ = GENERATOR.make_case(parent_seeds[0], "overlapping_clusters", dimension, first_rank, "parent_first")
                second, second_witness, _ = GENERATOR.make_case(parent_seeds[1], "overlapping_clusters", dimension, rank - first_rank, "parent_second")
                first_basis = np.asarray(first_witness["orbital"])
                second_basis = np.asarray(second_witness["orbital"])
                first_roots = np.tensordot(np.asarray(first_witness["auxiliary"]), np.asarray(first["factors"]), axes=(1, 0))
                second_roots = np.tensordot(np.asarray(second_witness["auxiliary"]), np.asarray(second["factors"]), axes=(1, 0))
                strength = float(generator.uniform(lower, upper))
                root_scales = generator.uniform(0.75, 1.35, rank)
                roots = np.concatenate((first_roots, strength * second_roots)) * root_scales[:, None, None]
                block = block_diag(GENERATOR.orthogonal(generator, first_rank), GENERATOR.orthogonal(generator, rank - first_rank))
                skew = generator.normal(size=(rank, rank))
                skew = (skew - skew.T) / math.sqrt(rank)
                gauge_strength = 0.12 if dimension == 14 else 0.20
                mixing = expm(gauge_strength * skew) @ block
                factors = np.tensordot(mixing, roots, axes=(1, 0))
                one_body = (np.asarray(first["one_body"]) + strength * np.asarray(second["one_body"])) / (1 + strength)
                case = {"id": identifier, "family": "competing_nearblock_gauge", "one_body": one_body.tolist(), "factors": factors.tolist()}
                baseline = BASELINE.solve(case)
                scaling_cost = validate_solution(case, baseline)
                optimizer_case = dict(case, baseline_cost=scaling_cost)
                gram = factors.reshape(rank, -1) @ factors.reshape(rank, -1).T
                gram_auxiliary = np.linalg.eigh(gram)[1].T
                candidates = [
                    ("first_planted", witness(identifier, first_basis, mixing.T)),
                    ("second_planted", witness(identifier, second_basis, mixing.T)),
                    ("first_gram", witness(identifier, first_basis, gram_auxiliary)),
                    ("second_gram", witness(identifier, second_basis, gram_auxiliary)),
                    ("interpolated_035", witness(identifier, polar(0.65 * first_basis + 0.35 * second_basis), mixing.T)),
                    ("interpolated_065", witness(identifier, polar(0.35 * first_basis + 0.65 * second_basis), mixing.T)),
                    ("spectral_start", baseline),
                ]
                for _, candidate in candidates:
                    validate_solution(case, candidate)
                starts[identifier] = [{"label": label, "solution": candidate} for label, candidate in candidates]
                flattened = roots.reshape(rank, -1)
                observed = factors.reshape(rank, -1)
                invariant = flattened.T @ flattened
                residual = np.linalg.norm(invariant - observed.T @ observed) / np.linalg.norm(invariant)
                native_costs = []
                support_residuals = []
                for root_group, native_basis in ((roots[:first_rank], first_basis), (roots[first_rank:], second_basis)):
                    row = []
                    for orbital in (first_basis, second_basis):
                        rotated = np.stack([orbital.T @ factor @ orbital for factor in root_group])
                        weights = np.abs(rotated).sum(axis=(1, 2))
                        row.append(float(0.5 * weights @ weights))
                    native_costs.append(row)
                    for factor_index, factor in enumerate(root_group):
                        local = native_basis.T @ factor @ native_basis
                        center = (3 * factor_index + factor_index // 3) % dimension
                        sites = [(center + offset) % dimension for offset in range(3)]
                        mask = np.ones((dimension, dimension), dtype=bool)
                        mask[np.ix_(sites, sites)] = False
                        support_residuals.append(float(np.linalg.norm(local[mask])))
                physical_spectrum = spectrum(case)
                public_separations = {name: float(np.linalg.norm(physical_spectrum - values) / max(np.linalg.norm(physical_spectrum), np.linalg.norm(values))) for name, values in public_spectra.items() if len(values) == dimension}
                minimum_eigenvalue = float(min(np.linalg.eigvalsh(factor).min() for factor in roots))
                proof = {
                    "id": identifier, "seed": seed, "parent_seeds": parent_seeds, "dimension": dimension, "rank": rank,
                    "strength_regime": regime, "regime_bounds": [lower, upper], "replicate": replicate,
                    "relative_strength": strength, "root_scales": root_scales.tolist(), "auxiliary_skew_strength": gauge_strength,
                    "source_family": "overlapping_clusters", "localized_support_width": 3, "diffuse_added": False,
                    "minimum_root_eigenvalue": minimum_eigenvalue,
                    "hermiticity_residual": float(max(np.linalg.norm(one_body - one_body.T), np.linalg.norm(factors - factors.transpose(0, 2, 1)))),
                    "squared_operator_tensor_relative_residual": float(residual), "maximum_native_support_residual": max(support_residuals),
                    "unmixed_family_costs_in_planted_bases": native_costs,
                    "both_families_prefer_own_basis": native_costs[0][0] < native_costs[0][1] and native_costs[1][1] < native_costs[1][0],
                    "one_particle_sector_spectrum": physical_spectrum.tolist(), "public_spectral_separations": public_separations,
                    "no_prior_parent_seed_reused": True, "original_spectral_scaling_cost": scaling_cost,
                    "hypothesized_root_cause": "Competing orbital-locality basins and near-block auxiliary mixing; no champion failure has been tested.",
                }
                if minimum_eigenvalue < -1e-8 or residual > 1e-10 or max(support_residuals) > 1e-8:
                    raise ValueError("Invalid PSD/locality/gauge certificate")
                if public_separations and min(public_separations.values()) <= 1e-6:
                    raise ValueError("Case is not demonstrably independent of public spectra")
                cases.append(case)
                inputs.append(optimizer_case)
                proofs.append(proof)
    separations = []
    for first_index, first in enumerate(proofs):
        for second in proofs[first_index + 1:]:
            if first["dimension"] != second["dimension"]:
                continue
            first_spectrum = np.asarray(first["one_particle_sector_spectrum"])
            second_spectrum = np.asarray(second["one_particle_sector_spectrum"])
            separation = float(np.linalg.norm(first_spectrum - second_spectrum) / max(np.linalg.norm(first_spectrum), np.linalg.norm(second_spectrum)))
            separations.append(separation)
    if min(separations) <= 1e-6:
        raise ValueError("Pool contains a potential spectral duplicate")
    write_json("cases.json", {"cases": cases, "seconds_per_case": 10, "reference_calibration_required": True, "warning": "baseline_cost intentionally absent: actual champion references have not been measured. This is an unscored physical pool, not a participant request or generation."})
    write_json("optimizer_inputs.json", {"cases": inputs, "seconds_per_case": 10, "warning": "PRIVATE OPTIMIZER ONLY: baseline_cost is original spectral scaling, NOT a generation-1/champion scoring reference. Never use these denominators for task scores."})
    write_json("planted_starts.json", starts)
    write_json("provenance.json", {"cases": proofs, "minimum_pairwise_same_dimension_spectral_separation": min(separations), "spectral_identity": "On N=1, H = h + 0.5*sum(B_k@B_k); its spectrum is invariant under the allowed gauges.", "root_cause_status": "Ex-ante structural hypotheses only; no tested champion2 failure."})
    return cases, inputs, proofs, starts


def optimize(cases, inputs, proofs, starts, arguments):
    solutions, references, history = {}, {}, []
    for case in cases:
        entries = starts[case["id"]]
        best = min(entries, key=lambda entry: validate_solution(case, entry["solution"]))
        solutions[case["id"]] = best["solution"]
        references[case["id"]] = {"id": case["id"], "initial_cost": validate_solution(case, best["solution"]), "absolute_cost": validate_solution(case, best["solution"]), "winning_start": best["label"], "attempts": 0, "optimizer_cpu_seconds": 0.0}
    def save():
        write_json("private_solution.json", {"solutions": [solutions[case["id"]] for case in cases]})
        write_json("private_references.json", {"kind": "Independently validated feasible upper bounds, not global optima or champion scoring references.", "records": list(references.values())})
        write_json("optimization_history.json", history)
    save()
    generator = np.random.default_rng(920041)
    budget_exhausted = False
    for round_index in range(arguments.rounds):
        order = generator.permutation(len(cases))
        for case_index in order:
            remaining = arguments.cpu_budget - 30 - time.process_time()
            if remaining < 0.5:
                budget_exhausted = True
                break
            case = cases[case_index]
            identifier = case["id"]
            entries = starts[identifier]
            if round_index < len(entries):
                label = entries[round_index]["label"]
                starting = entries[round_index]["solution"]
            else:
                label = f"best_jolt_{round_index - len(entries)}"
                seed = proofs[case_index]["seed"] + round_index * 719
                random = np.random.default_rng(seed)
                orbital = np.asarray(solutions[identifier]["orbital"]).copy()
                auxiliary = np.asarray(solutions[identifier]["auxiliary"]).copy()
                scale = (0.015, 0.05, 0.15, 0.30, 0.08)[(round_index - len(entries)) % 5]
                for matrix in (orbital, auxiliary):
                    skew = random.normal(size=matrix.shape)
                    skew = (skew - skew.T) / math.sqrt(len(matrix))
                    matrix[:] = matrix @ expm(scale * skew)
                starting = witness(identifier, orbital, auxiliary)
            before = time.process_time()
            candidate, diagnostic = PORTFOLIO.optimize(inputs[case_index], starting, min(arguments.seconds_per_start, remaining))
            measured = validate_solution(case, candidate)
            if abs(measured - diagnostic["cost"]) > 1e-8 * max(1, measured):
                raise ValueError("Optimizer and independent evaluator costs disagree")
            spent = time.process_time() - before
            record = references[identifier]
            improved = measured < record["absolute_cost"]
            if improved:
                solutions[identifier] = candidate
                record["absolute_cost"] = measured
                record["winning_start"] = label
            record["attempts"] += 1
            record["optimizer_cpu_seconds"] += spent
            history.append({"id": identifier, "round": round_index, "start": label, "absolute_cost": measured, "cpu_seconds": spent, "evaluations": diagnostic["evaluations"], "improved": improved})
        save()
        print(json.dumps({"phase": "optimization", "completed_round": round_index, "attempts": len(history), "process_cpu_seconds": time.process_time(), "budget_exhausted": budget_exhausted}), flush=True)
        if budget_exhausted:
            break
    return solutions, references, history, budget_exhausted


def finish(cases, proofs, starts, solutions, references, history, snapshot, mismatches, arguments, started, budget_exhausted):
    changes = [name for name, digest in snapshot.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changes:
        raise ValueError(f"Read-only source changes detected: {changes}")
    clusters = defaultdict(list)
    max_orthogonality = 0.0
    for case, proof in zip(cases, proofs):
        identifier = case["id"]
        solution = solutions[identifier]
        measured = validate_solution(case, solution)
        if abs(measured - references[identifier]["absolute_cost"]) > 1e-9 * max(1, measured):
            raise ValueError("Saved private reference disagrees with validation")
        for name in ("orbital", "auxiliary"):
            matrix = np.asarray(solution[name])
            max_orthogonality = max(max_orthogonality, float(np.linalg.norm(matrix.T @ matrix - np.eye(len(matrix)))))
        anchor = min(starts[identifier], key=lambda entry: validate_solution(case, entry["solution"]))["solution"]
        orbital_only = dict(anchor, orbital=solution["orbital"])
        auxiliary_only = dict(anchor, auxiliary=solution["auxiliary"])
        references[identifier]["orbital_only_from_best_initial_cost"] = validate_solution(case, orbital_only)
        references[identifier]["auxiliary_only_from_best_initial_cost"] = validate_solution(case, auxiliary_only)
        clusters[f"n{proof['dimension']}/{proof['strength_regime']}"].append(identifier)
    write_json("private_references.json", {"kind": "Quality-feasible upper bounds only. No contender has been evaluated and no task reference denominator is calibrated.", "records": list(references.values())})
    write_json("rootcause_clusters.json", {"status": "Structural hypotheses, not validated failure clusters", "clusters": dict(clusters), "cases_with_both_native_preferences": sum(proof["both_families_prefer_own_basis"] for proof in proofs), "private_one_gauge_ablation_records": "private_references.json"})
    report = {
        "ready_for_later_private_audit": True, "production_reference_calibration_required": True,
        "participant_generation_created": False, "fresh_outputs_read": False, "contender_evaluations": 0,
        "cases": len(cases), "dimensions": sorted({proof["dimension"] for proof in proofs}), "ranks": sorted({proof["rank"] for proof in proofs}),
        "cpu": arguments.cpu, "process_cpu_seconds": time.process_time(), "wall_seconds": time.monotonic() - started,
        "configured_cpu_budget_seconds": arguments.cpu_budget, "hard_cpu_limit_seconds": 900, "cpu_budget_exhausted": budget_exhausted,
        "optimizer_attempts": len(history), "minimum_attempts_per_case": min(record["attempts"] for record in references.values()),
        "all_private_witnesses_valid": True, "maximum_orthogonality_residual": max_orthogonality,
        "minimum_root_eigenvalue": min(proof["minimum_root_eigenvalue"] for proof in proofs),
        "maximum_tensor_identity_relative_residual": max(proof["squared_operator_tensor_relative_residual"] for proof in proofs),
        "maximum_native_support_residual": max(proof["maximum_native_support_residual"] for proof in proofs),
        "cases_with_genuine_competing_native_preferences": sum(proof["both_families_prefer_own_basis"] for proof in proofs),
        "frozen_sources_unchanged": True, "preexisting_freeze_manifest_mismatches": mismatches,
        "future_audit_rule": "Only audit a completed authorized champion. Calibrate actual reference costs separately; retain 10*N runtime in any future task. Do not use optimizer_inputs.json's spectral scaling denominators as champion references.",
        "limits": "Exploratory provenance only if the current fresh attempt fails. No hardness, target pass, global optimum, or runtime-valid unprivileged solver is claimed.",
    }
    write_json("report.json", report)
    print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", type=int, default=187)
    parser.add_argument("--cpu-budget", type=float, default=720)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--seconds-per-start", type=float, default=6)
    arguments = parser.parse_args()
    if arguments.cpu == 188 or arguments.cpu not in os.sched_getaffinity(0):
        raise ValueError("Private CPU must be allowed and must not be CPU 188")
    if not 60 <= arguments.cpu_budget <= 840:
        raise ValueError("CPU budget must leave a safety reserve below 15 minutes")
    os.sched_setaffinity(0, {arguments.cpu})
    resource.setrlimit(resource.RLIMIT_CPU, (885, 900))
    started = time.monotonic()
    snapshot, mismatches = source_snapshot()
    write_json("source_hashes.json", snapshot)
    write_json("config.json", {"cpu": arguments.cpu, "cpu_budget_seconds": arguments.cpu_budget, "hard_cpu_limit_seconds": 900, "rounds": arguments.rounds, "seconds_per_start": arguments.seconds_per_start, "cases": 24, "dimensions": [14, 16], "ranks": [12, 14], "relative_strength_range": [0.75, 1.35], "root_scale_range": [0.75, 1.35], "auxiliary_skew_strength_by_dimension": {"14": 0.12, "16": 0.20}, "localized_support_width": 3, "independent_parent_families": 2, "diffuse_added": False, "seed_base": 82940821, "seed_stride": 10007, "pending_reference_calibration": True, "no_fresh_or_champion_evaluation": True})
    cases, inputs, proofs, starts = make_pool()
    print(json.dumps({"phase": "generated", "cases": len(cases), "cpu": arguments.cpu, "process_cpu_seconds": time.process_time()}), flush=True)
    solutions, references, history, exhausted = optimize(cases, inputs, proofs, starts, arguments)
    finish(cases, proofs, starts, solutions, references, history, snapshot, mismatches, arguments, started, exhausted)


if __name__ == "__main__":
    main()
