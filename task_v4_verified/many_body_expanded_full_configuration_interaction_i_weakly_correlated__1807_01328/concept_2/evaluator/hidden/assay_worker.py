import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


HIDDEN = Path(__file__).resolve().parent
SPEC = json.loads((HIDDEN / "assay_spec.json").read_text())
MODULE_SPEC = importlib.util.spec_from_file_location("independent_nominal", HIDDEN / "verify.py")
NOMINAL = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(NOMINAL)
FAMILIES = ("vv", "full")
DIMENSIONS = {"vv": 42, "full": 100}
PHYSICAL_FLAGS = ("hf_weight", "spectral_gap", "diagonal_margin")
NUMERICAL_FLAGS = ("eigen_residual", "closure", "variational", "solver_agreement")
METRIC_FIELDS = ("full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "tail_to_parent_ratio", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh")


def hidden_uniforms():
    payload = (HIDDEN / "uniforms.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != SPEC["hidden_uniforms_sha256"]:
        raise ValueError("hidden draw commitment mismatch")
    if hashlib.sha256((HIDDEN / "target.json").read_bytes()).hexdigest() != SPEC["nominal_target_sha256"]:
        raise ValueError("nominal target commitment mismatch")
    parsed = json.loads(payload)["families"]
    if set(parsed) != set(FAMILIES):
        raise ValueError("unexpected hidden families")
    pools = {family: np.asarray(parsed[family], dtype=float) for family in FAMILIES}
    for family, values in pools.items():
        if values.shape != (SPEC["hidden_case_count_per_family"], DIMENSIONS[family]):
            raise ValueError("incorrect hidden pool shape")
        if not np.all(np.isfinite(values)) or np.any(values < 0) or np.any(values >= 1):
            raise ValueError("invalid hidden uniform")
    return pools


def perturb(coefficients, uniforms, family):
    if family not in FAMILIES:
        raise ValueError("unknown family")
    directions = np.asarray(uniforms, dtype=float)
    if directions.shape != (DIMENSIONS[family],) or not np.all(np.isfinite(directions)) or np.any(directions < 0) or np.any(directions >= 1):
        raise ValueError("invalid perturbation row")
    energies, hopping, density = [np.array(entries, dtype=float, copy=True) for entries in coefficients]
    pairs = [(source, destination) for source in range(3 if family == "vv" else 0, 10) for destination in range(source + 1, 10)]
    center = np.array([matrix[source, destination] for matrix in (hopping, density) for source, destination in pairs])
    bounds = np.array([NOMINAL.TARGET["hopping_bound_eh"]] * len(pairs) + [NOMINAL.TARGET["density_bound_eh"]] * len(pairs))
    offset = 0
    if family == "full":
        energies = energies + SPEC["delta_eh"] * (2.0 * directions[:10] - 1.0)
        offset = 10
    lower = np.maximum(center - SPEC["delta_eh"], -bounds)
    upper = np.minimum(center + SPEC["delta_eh"], bounds)
    changes = lower + (upper - lower) * directions[offset:]
    for matrix_index, matrix in enumerate((hopping, density)):
        for pair_index, (source, destination) in enumerate(pairs):
            matrix[source, destination] = matrix[destination, source] = changes[matrix_index * len(pairs) + pair_index]
    return energies, hopping, density


def evaluate_case(coefficients):
    metrics = NOMINAL.calculate_coefficients(coefficients)
    assessment = NOMINAL.assess(metrics)
    if "admissibility" not in assessment:
        raise ValueError("nonfinite numerical diagnostic")
    numerical = all(assessment["admissibility"][name] for name in NUMERICAL_FLAGS)
    assessment["numerical_valid"] = numerical
    assessment["metrics"] = {field: metrics[field] for field in METRIC_FIELDS}
    assessment["max_numerical_error_eh"] = max(metrics[name] for name in ("eigen_residual_eh", "closure_error_eh", "variational_violation_eh", "full_solver_disagreement_eh"))
    return assessment


def summarize(cases):
    failure_counts, clusters, physical_counts = collections.Counter(), collections.Counter(), collections.Counter()
    for case in cases:
        failed = []
        if not case["numerical_valid"]:
            failed.append("numerical")
        physical = [name for name in PHYSICAL_FLAGS if not case["admissibility"][name]]
        physical_counts.update(physical)
        if physical:
            failed.append("physical")
        for key, label in (("all_triples_small", "parents"), ("material_tail", "material_tail"), ("large_ratio", "ratio")):
            if not case["witness_checks"][key]:
                failed.append(label)
        failure_counts.update(failed)
        clusters["+".join(failed) if failed else "pass"] += 1
    count = len(cases)
    successes = sum(case["passed"] for case in cases)
    return dict(case_count=count, required_successes=math.ceil(SPEC["min_success_fraction"] * count),
                successes=successes, success_fraction=successes / count,
                physically_valid_cases=sum(all(case["admissibility"][name] for name in PHYSICAL_FLAGS) for case in cases),
                numerically_valid_cases=sum(case["numerical_valid"] for case in cases),
                failure_counts_nonexclusive=dict(failure_counts), failure_clusters=dict(clusters),
                physical_failure_counts=dict(physical_counts),
                metric_ranges={field: dict(min=min(case["metrics"][field] for case in cases), max=max(case["metrics"][field] for case in cases)) for field in METRIC_FIELDS},
                minimum_individual_nominal_score=min(case["core_score"] for case in cases),
                max_numerical_error_eh=max(case["max_numerical_error_eh"] for case in cases))


def combine(nominal, cases):
    if set(cases) != set(FAMILIES):
        raise ValueError("both families are required")
    summaries = {family: summarize(cases[family]) for family in FAMILIES}
    valid = nominal["valid"] and all(case["numerical_valid"] for family in FAMILIES for case in cases[family])
    scores = {"nominal": nominal["core_score"]}
    scores.update({family: min(1.0, summaries[family]["success_fraction"] / SPEC["min_success_fraction"]) for family in FAMILIES})
    passed = valid and nominal["passed"] and all(summaries[family]["successes"] >= summaries[family]["required_successes"] for family in FAMILIES)
    return dict(valid=valid, passed=passed,
                reason="nominal and both frozen robustness families pass" if passed else ("admissible, one or more targets not met" if valid else "inadmissible nominal or unverified numerical case"),
                core_score=math.fsum(scores.values()) / 3 if valid else 0.0,
                worst_family_score=min(scores.values()) if valid else 0.0,
                family_scores=scores, nominal=nominal, robustness_families=summaries,
                resource_score=1.0, evaluation_complete=True)


def evaluate(path):
    started = time.perf_counter()
    try:
        hopping, density = NOMINAL.read_candidate(path)
        center = NOMINAL.full_coefficients(hopping, density)
        directions = hidden_uniforms()
        nominal = evaluate_case(center)
        cases = {family: [evaluate_case(perturb(center, row, family)) for row in directions[family]] for family in FAMILIES}
        report = combine(nominal, cases)
    except (ValueError, TypeError, OSError, OverflowError, RecursionError, MemoryError, np.linalg.LinAlgError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0,
                      reason="invalid witness or validation error: " + str(error), resource_score=0.0, evaluation_complete=False)
    report.update(worker_runtime_seconds=time.perf_counter() - started,
                  peak_memory_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0)
    return report


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_AS, (SPEC["evaluator_memory_mib"] * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (SPEC["evaluator_cpu_seconds"],) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = evaluate(sys.argv[1])
    result["resource_limits"] = dict(address_space_bytes=resource.getrlimit(resource.RLIMIT_AS)[0], cpu_seconds=resource.getrlimit(resource.RLIMIT_CPU)[0], core_dump_bytes=resource.getrlimit(resource.RLIMIT_CORE)[0])
    print(json.dumps(result, allow_nan=False))
