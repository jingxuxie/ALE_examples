import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parents[1] / "pilots/free_energy"
PHYSICAL = [0, 1, 2, 5, 6, 7, 8]
NAMES = ["torque", "magnetization", "energy", "constraint_drift", "norm_error",
         "lower_perpendicular", "upper_perpendicular", "surface_parallel",
         "surface_perpendicular", "acceptance"]


def statistics(blocks):
    chains, count, columns = blocks.shape
    means = blocks.mean(axis=1)
    within = np.var(blocks, axis=1, ddof=1).mean(axis=0)
    between = count * np.var(means, axis=0, ddof=1)
    rhat = np.sqrt(np.maximum(0, ((count - 1) * within + between) /
                             (count * np.maximum(within, 1e-30))))
    sem = np.std(means, axis=0, ddof=1) / math.sqrt(chains)
    groups = []
    for grouping in [1, 2, 5, 10, 25, 50]:
        if count % grouping or count // grouping < 4:
            continue
        grouped = blocks.reshape(chains, count // grouping, grouping, columns).mean(axis=2)
        errors = np.sqrt(np.var(grouped, axis=1, ddof=1).mean(axis=0) /
                         (chains * (count // grouping)))
        sem = np.maximum(sem, errors)
        groups.append(grouping)
    return means.mean(axis=0), sem, rhat, groups


def load(case_id, kind, angle, chain_count):
    plan_path = ROOT / "reference/refinement_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        replacement = plan["replacements"].get(f"{case_id}:{kind}:{angle:.10f}")
        if replacement:
            kind = replacement["raw_kind"]
            chain_count = replacement["chains"]
    arrays, provenance = [], []
    for chain in range(chain_count):
        path = ROOT / "reference/raw" / f"{case_id}_{kind}_{angle:.10f}_{chain}.npz"
        with np.load(path, allow_pickle=False) as archive:
            arrays.append(archive["blocks"])
            provenance.append({"path": str(path.relative_to(ROOT)),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                               "seed": int(archive["seed"]), "start": str(archive["start"]),
                               "burn": int(archive["burn"]), "sweeps": int(archive["sweeps"]),
                               "elapsed": float(archive["seconds"])})
    blocks = np.asarray(arrays)
    mean, sem, rhat, groups = statistics(blocks)
    half = blocks.shape[1] // 2
    split = np.concatenate([blocks[:, :half], blocks[:, -half:]], axis=0)
    _, _, split_rhat, _ = statistics(split)
    return {"angle": angle, "raw_kind": kind, "mean": mean, "sem": sem, "rhat": rhat,
            "split_rhat": split_rhat, "chain_means": blocks.mean(axis=1),
            "max_constraint_drift": float(np.abs(blocks[:, :, 3]).max()),
            "max_norm_error": float(np.abs(blocks[:, :, 4]).max()),
            "block_grouping_sweeps": [200 * group for group in groups], "provenance": provenance}


def integration_matrix(grid, requested):
    step = grid[1] - grid[0]
    weights = np.zeros((len(requested), len(grid)))
    for row, angle in enumerate(requested):
        stop = int(round(angle / step))
        assert abs(grid[stop] - angle) < 1e-12 and stop % 2 == 0
        if stop:
            weights[row, :stop + 1] = 2
            weights[row, 1:stop:2] = 4
            weights[row, 0] = weights[row, stop] = 1
    return weights * step / 3


def serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serializable(value), indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    arguments = parser.parse_args()
    case_id = arguments.case
    case = json.loads((ROOT / "cases" / f"{case_id}.json").read_text())
    protocol = json.loads((ROOT / "validation_protocol.json").read_text())
    requested = np.asarray(case["angles"])
    coarse_grid = np.linspace(0, math.pi / 2, 17)
    fine_grid = np.linspace(0, math.pi / 2, 33)
    gold = [load(case_id, "gold", angle, 4) for angle in coarse_grid]
    strong = [load(case_id, "strong", angle, 2) for angle in coarse_grid]
    midpoint = [load(case_id, "midpoint", angle, 2) for angle in fine_grid[1::2]]
    reflection = load(case_id, "reflection", -math.pi / 4, 2)
    fine = [gold[index // 2] if index % 2 == 0 else midpoint[index // 2] for index in range(33)]
    all_records = gold + strong + midpoint + [reflection]
    source_provenance = json.loads((ROOT / "source_provenance.json").read_text())
    for name, metadata in source_provenance["files"].items():
        for path in [Path(metadata["original"]), ROOT / "reference/source" / name]:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
    seeds = [item["seed"] for record in all_records for item in record["provenance"]]
    assert len(set(seeds)) == len(seeds)
    evaluator_path = PILOT / "private/evaluator.py"
    evaluator_hash = hashlib.sha256(evaluator_path.read_bytes()).hexdigest()
    assert evaluator_hash == "54feda4dfa0a21bac57e2877aee6c143cd79cd425b15ed028e294a958bc51ecf"
    specification = importlib.util.spec_from_file_location("trusted_frozen_evaluator", evaluator_path)
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    coarse_weights = integration_matrix(coarse_grid, requested)
    fine_weights = integration_matrix(fine_grid, requested)
    fine_mean = np.array([record["mean"][0] for record in fine])
    fine_sem = np.array([record["sem"][0] for record in fine])
    strong_mean = np.array([record["mean"][0] for record in strong])
    strong_sem = np.array([record["sem"][0] for record in strong])
    endpoint_z = [abs(record["mean"][0]) / max(record["sem"][0], 1e-15)
                  for records in [gold, strong] for record in [records[0], records[-1]]]
    reflection_z = []
    for column in PHYSICAL:
        sign = -1 if column in [0, 5, 6, 8] else 1
        difference = reflection["mean"][column] - sign * gold[8]["mean"][column]
        uncertainty = math.hypot(reflection["sem"][column], gold[8]["sem"][column])
        reflection_z.append(abs(difference) / max(uncertainty, 1e-15))
    fine_mean[[0, -1]] = 0
    fine_sem[[0, -1]] = 0
    strong_mean[[0, -1]] = 0
    strong_sem[[0, -1]] = 0
    fine_indices = np.rint(requested / fine_grid[1]).astype(int)
    coarse_indices = np.rint(requested / coarse_grid[1]).astype(int)
    reference = {"version": 1, "case_id": case_id, "angles": requested,
                 "torque": fine_mean[fine_indices], "torque_sem": fine_sem[fine_indices],
                 "free_energy": -fine_weights @ fine_mean,
                 "free_energy_sem": np.sqrt(fine_weights ** 2 @ fine_sem ** 2)}
    independent = {"version": 1, "case_id": case_id,
                   "torque": strong_mean[coarse_indices], "torque_sem": strong_sem[coarse_indices],
                   "free_energy": -coarse_weights @ strong_mean,
                   "free_energy_sem": np.sqrt(coarse_weights ** 2 @ strong_sem ** 2)}
    strong_score, strong_components = evaluator.score(case, reference, independent)
    baseline_score, baseline_components = evaluator.score(case, reference, evaluator.baseline(case))
    difference_weights = -fine_weights.copy()
    difference_weights[:, ::2] += coarse_weights
    quadrature_difference = difference_weights @ fine_mean
    quadrature_sem = np.sqrt(difference_weights ** 2 @ fine_sem ** 2)
    baseline_free_rmse = strong_components["free_energy"]["baseline_rmse"]
    quadrature_bound = float(np.sqrt(np.mean((np.abs(quadrature_difference) + 1.96 * quadrature_sem) ** 2)))
    quadrature_fraction = quadrature_bound / max(baseline_free_rmse, 1e-5)
    independent_z = []
    for first, second in zip(gold, strong):
        for column in PHYSICAL:
            deviation = abs(first["mean"][column] - second["mean"][column])
            uncertainty = math.hypot(first["sem"][column], second["sem"][column])
            independent_z.append({"angle": first["angle"], "observable": NAMES[column],
                                  "combined_sem_units": deviation / max(uncertainty, 1e-15)})
    worst_rhat = max((record["rhat"][column], record["angle"], NAMES[column])
                     for record in all_records for column in PHYSICAL)
    worst_split = max((record["split_rhat"][column], record["angle"], NAMES[column])
                      for record in all_records for column in PHYSICAL)
    quadrature_z = float(np.max(np.abs(quadrature_difference) / np.maximum(quadrature_sem, 1e-15)))
    gates = {
        "rhat": worst_rhat[0] < protocol["rhat_limit"],
        "split_rhat": worst_split[0] < protocol["split_rhat_limit"],
        "independent_chains": max(item["combined_sem_units"] for item in independent_z) < protocol["independent_chain_max_combined_sem_units"],
        "endpoint_symmetry": max(endpoint_z) < protocol["symmetry_max_combined_sem_units"],
        "reflection_symmetry": max(reflection_z) < protocol["symmetry_max_combined_sem_units"],
        "constraint": max(record["max_constraint_drift"] for record in all_records) < protocol["constraint_drift_limit"],
        "norm": max(record["max_norm_error"] for record in all_records) < protocol["norm_error_limit"],
        "quadrature_statistical_agreement": quadrature_z < protocol["quadrature_difference_max_sem_units"],
        "quadrature_physical_error_bound": quadrature_fraction < protocol["quadrature_95_bound_max_baseline_fraction"],
        "independent_strong_score": strong_score > protocol["strong_score_minimum"]}
    valid = all(gates.values())
    diagnostics = {"case_id": case_id, "reference_valid": valid, "gates": gates,
                   "protocol_sha256": hashlib.sha256((ROOT / "validation_protocol.json").read_bytes()).hexdigest(),
                   "evaluator_sha256": evaluator_hash, "worst_rhat": worst_rhat,
                   "worst_split_rhat": worst_split, "independent_comparisons": independent_z,
                   "endpoint_symmetry_sem_units": endpoint_z, "reflection_symmetry_sem_units": reflection_z,
                   "quadrature_difference": quadrature_difference, "quadrature_difference_sem": quadrature_sem,
                   "quadrature_95_bound_baseline_fraction": quadrature_fraction,
                   "trajectory_count": len(seeds), "records": {"gold": gold, "midpoint": midpoint,
                                                               "strong": strong, "reflection": reflection},
                   "uncertainty_interpretation": "Block SEM and normal pointwise 1.96-SEM envelopes, not simultaneous confidence bands or rigorous global mixing/truncation bounds.",
                   "limits": protocol["limits"]}
    folder = ROOT / "reference/results" / case_id
    write_json(folder / "reference.json", dict(reference, reference_valid=valid))
    write_json(folder / "strong_prediction.json", independent)
    write_json(folder / "validation.json", diagnostics)
    write_json(folder / "strong_reference_scores.json", {"score": strong_score, "components": strong_components,
                                                         "reference_valid": valid, "independent_seeds": True})
    write_json(folder / "baseline_scores.json", {"score": baseline_score, "components": baseline_components,
                                                 "reference_valid": valid})
    result = {"case_id": case_id, "reference_valid": valid, "strong_score": strong_score,
              "gates": gates, "worst_rhat": worst_rhat, "worst_split_rhat": worst_split,
              "quadrature_95_bound_baseline_fraction": quadrature_fraction}
    output = ROOT / "submissions" / case_id / "output.json"
    execution_path = output.with_name("execution.json")
    if execution_path.exists():
        execution = json.loads(execution_path.read_text())
        result["runtime_seconds"] = execution["elapsed"]
        if execution["returncode"] == 0 and not execution["timeout"]:
            prediction = json.loads(output.read_text())
            assert prediction["case_id"] == case_id and prediction["version"] == 1
            candidate_score, candidate_components = evaluator.score(case, reference, prediction)
            result.update(submitted_score=candidate_score, components=candidate_components,
                          decision="REJECT_NO_FAILURE" if valid and candidate_score > 0.9 else
                                   "INVALID_REFERENCE" if not valid else "CANDIDATE_FAILURE_REQUIRES_REPLICATION")
        else:
            result.update(decision="SUBMISSION_FAILED" if valid else "INVALID_REFERENCE", execution=execution)
    else:
        result["decision"] = "PENDING_FULL_SUBMISSION"
    write_json(folder / "full_comparison.json", result)
    print(json.dumps(serializable(result), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
