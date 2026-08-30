import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.linalg import block_diag, expm


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import score, validate_solution


def module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


GENERATOR = module("trusted_competing_generator", "adversary/generate.py")
PORTFOLIO = module("trusted_competing_portfolio", "adversary/portfolio/solver.py")
BASELINE = module("trusted_competing_baseline", "participant/baseline/solver.py")


def write_json(name, value):
    destination = DIRECTORY / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False))
    temporary.replace(destination)


def read_json(name):
    return json.loads((DIRECTORY / name).read_text())


def solution(identifier, orbital, auxiliary):
    return {"id": identifier, "orbital": orbital.tolist(), "auxiliary": auxiliary.tolist()}


def generate():
    cases, provenance, starting_points = [], [], {}
    families = ("competing_mixed_strength", "competing_nearblock_gauge", "competing_strong_diffuse")
    for family_index, family in enumerate(families):
        for replicate in range(8):
            seed = 6281301 + family_index * 100003 + replicate * 1009
            generator = np.random.default_rng(seed)
            dimension = (10, 12, 14, 16)[replicate % 4]
            rank = dimension - 2
            first_rank = rank // 2
            identifier = f"competing_{family_index + 1}_{replicate + 1:02d}"
            source_family = "multiscale" if family_index == 2 else "overlapping_clusters"
            first, first_witness, _ = GENERATOR.make_case(seed + 17, source_family, dimension, first_rank, "first_parent")
            second, second_witness, _ = GENERATOR.make_case(seed + 53, source_family, dimension, rank - first_rank, "second_parent")
            first_basis = np.asarray(first_witness["orbital"])
            second_basis = np.asarray(second_witness["orbital"])
            first_roots = np.tensordot(np.asarray(first_witness["auxiliary"]), np.asarray(first["factors"]), axes=(1, 0))
            second_roots = np.tensordot(np.asarray(second_witness["auxiliary"]), np.asarray(second["factors"]), axes=(1, 0))
            relative_strength = (0.45, 0.65, 0.85, 1.0, 1.2, 0.55, 0.75, 1.35)[replicate]
            roots = np.concatenate((first_roots, relative_strength * second_roots))
            roots *= generator.uniform(0.75, 1.35, rank)[:, None, None]
            diffuse_strength = 0.0
            if family_index == 2:
                diffuse_strength = (0.25, 0.4, 0.65, 0.9)[replicate % 4]
                for factor_index in range(rank):
                    diffuse = generator.normal(size=(dimension, 2))
                    diffuse /= np.linalg.norm(diffuse)
                    roots[factor_index] += diffuse_strength * np.trace(roots[factor_index]) * (diffuse @ diffuse.T)
            if family_index == 1:
                block_rotation = block_diag(GENERATOR.orthogonal(generator, first_rank), GENERATOR.orthogonal(generator, rank - first_rank))
                skew = generator.normal(size=(rank, rank))
                skew = (skew - skew.T) / math.sqrt(rank)
                mixing = expm((0.035, 0.07, 0.12, 0.2)[replicate % 4] * skew) @ block_rotation
            else:
                mixing = GENERATOR.orthogonal(generator, rank)
            factors = np.tensordot(mixing, roots, axes=(1, 0))
            one_body = (np.asarray(first["one_body"]) + relative_strength * np.asarray(second["one_body"])) / (1 + relative_strength)
            case = {"id": identifier, "family": family, "one_body": one_body.tolist(), "factors": factors.tolist()}
            baseline = BASELINE.solve(case)
            case["baseline_cost"] = validate_solution(case, baseline)
            left, singular_values, right = np.linalg.svd(first_basis + second_basis)
            midpoint = left @ right
            starts = [solution(identifier, basis, mixing.T) for basis in (first_basis, second_basis, midpoint)]
            for starting in starts:
                validate_solution(case, starting)
            starting_points[identifier] = starts
            recovered = np.tensordot(mixing.T, factors, axes=(1, 0))
            before_gram = roots.reshape(rank, -1).T @ roots.reshape(rank, -1)
            after_gram = factors.reshape(rank, -1).T @ factors.reshape(rank, -1)
            commutator = first_roots[0] @ second_roots[0] - second_roots[0] @ first_roots[0]
            proof = {
                "id": identifier, "family": family, "seed": seed,
                "parent_seeds": [seed + 17, seed + 53], "source_family": source_family,
                "dimension": dimension, "rank": rank, "family_ranks": [first_rank, rank - first_rank],
                "relative_strength": relative_strength, "diffuse_strength": diffuse_strength,
                "prospective_split": "public" if replicate < 4 else "hidden",
                "minimum_root_eigenvalue": float(min(np.linalg.eigvalsh(factor).min() for factor in roots)),
                "symmetry_residual": float(np.linalg.norm(factors - factors.transpose(0, 2, 1))),
                "root_recovery_residual": float(np.linalg.norm(recovered - roots)),
                "squared_operator_tensor_relative_residual": float(np.linalg.norm(before_gram - after_gram) / np.linalg.norm(before_gram)),
                "normalized_cross_family_commutator": float(np.linalg.norm(commutator) / (np.linalg.norm(first_roots[0]) * np.linalg.norm(second_roots[0]))),
                "basis_overlap_fourth_moment": float(np.sum((first_basis.T @ second_basis) ** 4) / dimension),
                "midpoint_minimum_singular_value": float(singular_values.min()),
                "baseline_cost": case["baseline_cost"],
                "starting_costs": [validate_solution(case, starting) for starting in starts],
            }
            if proof["minimum_root_eigenvalue"] < -1e-8 or proof["squared_operator_tensor_relative_residual"] > 1e-10:
                raise ValueError("invalid PSD roots or auxiliary gauge identity")
            cases.append(case)
            provenance.append(proof)
    write_json("cases.json", {"cases": cases, "seconds_per_case": 10})
    write_json("starts.json", starting_points)
    write_json("provenance.json", {"distribution_extension": True, "numeric_contract": "10 <= n <= 16; 8 <= r <= 14", "rule": "Two independently seeded localized PSD charge families in independent Haar orbital bases, then an orthogonal auxiliary presentation. No secret identifiers enter the objective.", "cases": provenance})
    write_json("frozen_sources.json", {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "participant/TASK.md", ROOT / "participant/input/FORMAT.md", ROOT / "participant/baseline/solver.py", ROOT / "participant/workspace/objective.py", ROOT / "evaluator/evaluate.py")})
    print(json.dumps({"phase": "generated", "cases": len(cases)}), flush=True)


def optimize(seconds):
    request = read_json("cases.json")
    starts = read_json("starts.json")
    solutions, records = [], []
    for case in request["cases"]:
        started = time.monotonic()
        best = BASELINE.solve(case)
        best_cost = validate_solution(case, best)
        attempts = []
        for start_index, starting in enumerate(starts[case["id"]]):
            candidate, reported = PORTFOLIO.optimize(case, starting, seconds)
            measured = validate_solution(case, candidate)
            if abs(measured - reported["cost"]) > 1e-8 * max(1, measured):
                raise ValueError("private optimizer/evaluator objective disagreement")
            attempts.append(dict(start_index=start_index, independently_validated_cost=measured, **reported))
            if measured < best_cost:
                best, best_cost = candidate, measured
        record = {"id": case["id"], "family": case["family"], "cost": best_cost, "reduction": 1 - best_cost / case["baseline_cost"], "seconds": time.monotonic() - started, "attempts": attempts}
        records.append(record)
        solutions.append(best)
        write_json("private_solution.json", {"solutions": solutions})
        write_json("private_optimization.json", records)
        print(json.dumps({key: value for key, value in record.items() if key != "attempts"}), flush=True)
    write_json("private_score.json", score(request, {"solutions": solutions}, sum(record["seconds"] for record in records), artifact=True))


def evaluate_champion(submission):
    request = read_json("cases.json")
    for batch in range(2):
        selection = request["cases"][12 * batch:12 * (batch + 1)]
        prefix = f"champion/batch_{batch}"
        write_json(prefix + ".cases.json", {"cases": selection, "seconds_per_case": 10})
        command = ["/usr/bin/python3", str(ROOT.parent / "private/affinity.py"), str(ROOT / "adversary/capture_evaluate.py"), str(submission.resolve(strict=True)), "--cases", str(DIRECTORY / (prefix + ".cases.json")), "--report", str(DIRECTORY / (prefix + ".report.json")), "--response", str(DIRECTORY / (prefix + ".response.json"))]
        with (DIRECTORY / (prefix + ".log")).open("wb") as output:
            subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=215, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
        report = read_json(prefix + ".report.json")
        print(json.dumps({"phase": "champion", "batch": batch, "valid": report.get("valid"), "runtime": report.get("runtime_seconds"), "core_score": report.get("core_score"), "reason": report.get("reason")}), flush=True)


def summarize():
    request = read_json("cases.json")
    cases = {case["id"]: case for case in request["cases"]}
    private = {entry["id"]: entry for entry in read_json("private_solution.json")["solutions"]}
    provenance = {entry["id"]: entry for entry in read_json("provenance.json")["cases"]}
    records, failures, champion_solutions = [], [], []
    for batch in range(2):
        prefix = f"champion/batch_{batch}"
        report = read_json(prefix + ".report.json")
        if not report.get("valid"):
            failures.append({"batch": batch, "reason": report.get("reason"), "scientific_quality_gap": False})
            continue
        entries = read_json(prefix + ".response.json")["solutions"]
        champion_solutions.extend(entries)
        for candidate in entries:
            case = cases[candidate["id"]]
            champion_cost = validate_solution(case, candidate)
            private_cost = validate_solution(case, private[case["id"]])
            records.append({"id": case["id"], "family": case["family"], "seed": provenance[case["id"]]["seed"], "prospective_split": provenance[case["id"]]["prospective_split"], "baseline_cost": case["baseline_cost"], "champion_cost": champion_cost, "private_cost": private_cost, "champion_reduction": 1 - champion_cost / case["baseline_cost"], "private_reduction": 1 - private_cost / case["baseline_cost"], "attainable_extra_reduction": 1 - private_cost / champion_cost})
    clusters = defaultdict(list)
    for record in records:
        if record["attainable_extra_reduction"] >= 0.08:
            clusters[record["family"]].append(record["id"])
    scores = {}
    for name in ("champion", "private"):
        if records:
            families = {family: 1 - math.exp(np.mean([math.log(record[name + "_cost"] / record["baseline_cost"]) for record in records if record["family"] == family])) for family in {record["family"] for record in records}}
            scores[name] = {"core_score": 1 - math.exp(np.mean([math.log(record[name + "_cost"] / record["baseline_cost"]) for record in records])), "worst_family_score": min(families.values()), "family_scores": families}
    report = {"cases": len(cases), "valid_measured_cases": len(records), "failures": failures, "positive_gaps": sum(record["attainable_extra_reduction"] > 0 for record in records), "at_least_8_percent_gaps": sum(record["attainable_extra_reduction"] >= 0.08 for record in records), "maximum_attainable_extra_reduction": max((record["attainable_extra_reduction"] for record in records), default=None), "scores": scores, "physical_clusters": dict(clusters), "ready_for_new_target": False, "interpretation": "Private artifacts establish feasible quality only, not a runtime-valid unprivileged solver. Competing locality is a disclosed distribution extension; original participant and evaluator remain frozen. No failure or timeout counts as a scientific gap.", "records": records}
    write_json("report.json", report)
    write_json("champion_solution.json", {"solutions": champion_solutions})
    for split in ("public", "hidden"):
        selected = [record["id"] for record in records if record["attainable_extra_reduction"] >= 0.08 and record["prospective_split"] == split]
        write_json(f"candidates/{split}.json", {"cases": [cases[identifier] for identifier in selected], "seconds_per_case": 10})
        write_json(f"candidates/{split}.witnesses.json", {"solutions": [private[identifier] for identifier in selected]})
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("generate", "optimize", "champion", "summarize", "all"))
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument("--submission", type=Path, default=ROOT / "champions/generation_1")
    arguments = parser.parse_args()
    if 188 in os.sched_getaffinity(0):
        os.sched_setaffinity(0, {188})
    if arguments.phase in ("generate", "all"):
        generate()
    if arguments.phase in ("optimize", "all"):
        optimize(arguments.seconds)
    if arguments.phase in ("champion", "all"):
        evaluate_champion(arguments.submission)
    if arguments.phase in ("summarize", "all"):
        summarize()


if __name__ == "__main__":
    main()
