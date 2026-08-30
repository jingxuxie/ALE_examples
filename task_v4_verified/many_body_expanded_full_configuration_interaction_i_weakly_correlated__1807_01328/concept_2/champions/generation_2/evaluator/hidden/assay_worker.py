import collections
import hashlib
import importlib.util
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


HIDDEN = Path(__file__).resolve().parent
SPEC = json.loads((HIDDEN / "assay_spec.json").read_text())
MODULE_SPEC = importlib.util.spec_from_file_location("trusted_nominal", HIDDEN / "verify.py")
NOMINAL = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(NOMINAL)
FIELDS = ("virtual_hopping", "virtual_density")
EDGES = [(row, column) for row in range(7) for column in range(row + 1, 7)]
NUMERICAL_FLAGS = ("eigen_residual", "closure", "variational", "solver_agreement")
METRIC_FIELDS = ("full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "tail_to_parent_ratio", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh")


def hidden_uniforms():
    payload = (HIDDEN / "uniforms.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != SPEC["hidden_uniforms_sha256"]:
        raise ValueError("hidden assay integrity failure")
    values = np.array(json.loads(payload)["uniforms"], dtype=float)
    if values.shape != (128, 42) or not np.all(np.isfinite(values)) or np.any(values < 0) or np.any(values >= 1):
        raise ValueError("invalid trusted assay directions")
    return values


def perturb(candidate, uniforms):
    center = np.array([candidate[field][row][column] for field in FIELDS for row, column in EDGES], dtype=float)
    bounds = np.array([NOMINAL.TARGET["hopping_bound_eh"]] * 21 + [NOMINAL.TARGET["density_bound_eh"]] * 21)
    lower = np.maximum(-bounds, center - SPEC["delta_eh"])
    upper = np.minimum(bounds, center + SPEC["delta_eh"])
    values = lower + np.asarray(uniforms) * (upper - lower)
    result = {"schema_version": 1}
    for field_index, field in enumerate(FIELDS):
        matrix = [[0.0] * 7 for row in range(7)]
        for edge_index, (row, column) in enumerate(EDGES):
            matrix[row][column] = matrix[column][row] = float(values[field_index * 21 + edge_index])
        result[field] = matrix
    return result


def evaluate_case(candidate):
    metrics = NOMINAL.calculate(candidate["virtual_hopping"], candidate["virtual_density"])
    assessment = NOMINAL.assess(metrics)
    assessment["numerical_valid"] = all(assessment.get("admissibility", {}).get(flag, False) for flag in NUMERICAL_FLAGS)
    assessment["metrics"] = {field: metrics[field] for field in METRIC_FIELDS}
    assessment["max_numerical_error_eh"] = max(metrics[field] for field in ("eigen_residual_eh", "closure_error_eh", "variational_violation_eh", "full_solver_disagreement_eh"))
    return assessment


def combine(nominal, cases):
    count = len(cases)
    successes = sum(case["passed"] for case in cases)
    required = math.ceil(SPEC["min_success_fraction"] * count)
    fraction = successes / count
    numerical_valid = nominal["numerical_valid"] and all(case["numerical_valid"] for case in cases)
    valid = nominal["valid"] and numerical_valid
    nominal_score = nominal["core_score"]
    robust_score = min(1.0, fraction / SPEC["min_success_fraction"])
    passed = valid and nominal["passed"] and successes >= required
    failures = collections.Counter()
    clusters = collections.Counter()
    for case in cases:
        failed = [group + "." + key for group in ("admissibility", "witness_checks") for key, value in case.get(group, {}).items() if not value]
        failures.update(failed)
        clusters[" + ".join(sorted(failed)) or "pass"] += 1
    ranges = {field: {"min": min(case["metrics"][field] for case in cases), "max": max(case["metrics"][field] for case in cases)} for field in METRIC_FIELDS}
    if not numerical_valid:
        reason = "numerical validation failed"
    elif not nominal["valid"]:
        reason = "nominal Hamiltonian inadmissible"
    elif not nominal["passed"]:
        reason = "nominal witness conditions not met"
    elif not passed:
        reason = "perturbation assay success requirement not met"
    else:
        reason = "nominal witness and specified perturbation assay pass"
    return {
        "valid": valid,
        "passed": passed,
        "reason": reason,
        "core_score": 0.5 * (nominal_score + robust_score) if valid else 0.0,
        "worst_family_score": min(nominal_score, robust_score) if valid else 0.0,
        "family_scores": {"nominal": nominal_score, "perturbed_assay": robust_score},
        "nominal": nominal,
        "perturbed_assay": {
            "case_count": count,
            "required_successes": required,
            "successes": successes,
            "success_fraction": fraction,
            "physically_valid_cases": sum(case["valid"] for case in cases),
            "failure_counts_nonexclusive": dict(failures),
            "failure_clusters": dict(clusters),
            "metric_ranges": ranges,
            "minimum_individual_nominal_score": min(case["core_score"] for case in cases),
            "max_numerical_error_eh": max(case["max_numerical_error_eh"] for case in cases),
        },
        "resource_score": 1.0 if numerical_valid else 0.0,
        "evaluation_complete": True,
    }


def evaluate(path):
    started = time.perf_counter()
    try:
        hopping, density = NOMINAL.read_candidate(path)
        candidate = dict(schema_version=1, virtual_hopping=hopping, virtual_density=density)
        nominal = evaluate_case(candidate)
        cases = [evaluate_case(perturb(candidate, uniforms)) for uniforms in hidden_uniforms()]
        report = combine(nominal, cases)
    except (ValueError, TypeError, OSError, OverflowError, RecursionError, MemoryError, np.linalg.LinAlgError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, reason="invalid witness or validation error: " + str(error), resource_score=0.0, evaluation_complete=False)
    report.update(worker_runtime_seconds=time.perf_counter() - started, peak_memory_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0)
    return report


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_AS, (SPEC["evaluator_memory_mib"] * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (SPEC["evaluator_cpu_seconds"],) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    print(json.dumps(evaluate(sys.argv[1]), allow_nan=False))
