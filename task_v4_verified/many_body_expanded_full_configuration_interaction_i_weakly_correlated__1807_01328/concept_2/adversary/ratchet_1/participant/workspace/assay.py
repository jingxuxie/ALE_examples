import collections
import json
import math
from pathlib import Path

import numpy as np

import model


INPUT = Path(__file__).resolve().parents[1] / "input"
SPEC = json.loads((INPUT / "assay_spec.json").read_text())
FIELDS = ("virtual_hopping", "virtual_density")
EDGES = [(row, column) for row in range(7) for column in range(row + 1, 7)]
METRIC_FIELDS = ("full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "tail_to_parent_ratio", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh")


def training_uniforms(seed=None, samples=None):
    if seed is None and samples is None:
        return np.array(json.loads((INPUT / "training_uniforms.json").read_text())["uniforms"])
    count = 64 if samples is None else samples
    if not 1 <= count <= 512:
        raise ValueError("public sample count must be between 1 and 512")
    return np.random.default_rng(202608281 if seed is None else seed).random((count, 42))


def perturb(candidate, uniforms):
    if len(uniforms) != 42 or any(not math.isfinite(value) or value < 0 or value >= 1 for value in uniforms):
        raise ValueError("directions must contain 42 finite uniforms in [0,1)")
    result = {"schema_version": 1}
    for field_index, field in enumerate(FIELDS):
        bound = model.TARGET["hopping_bound_eh"] if field_index == 0 else model.TARGET["density_bound_eh"]
        matrix = [[0.0] * 7 for row in range(7)]
        for edge_index, (row, column) in enumerate(EDGES):
            center = candidate[field][row][column]
            lower = max(-bound, center - SPEC["delta_eh"])
            upper = min(bound, center + SPEC["delta_eh"])
            value = lower + float(uniforms[21 * field_index + edge_index]) * (upper - lower)
            matrix[row][column] = matrix[column][row] = value
        result[field] = matrix
    return result


def evaluate_case(candidate):
    metrics = model.compute(candidate, complete=True)
    assessment = model.score(metrics)
    energies = metrics["subset_energies_eh"]
    variational = max(0.0, max(energies[str(mask | (1 << index))] - energies[str(mask)] for mask in range(128) for index in range(7) if not mask & (1 << index)))
    errors = [metrics["eigen_residual_eh"], metrics["closure_error_eh"], abs(energies["127"] - metrics["full_energy_eh"]), variational]
    numerical_valid = all(math.isfinite(value) and value <= model.TARGET["numerical_check_eh"] for value in errors)
    assessment["numerical_valid"] = numerical_valid
    assessment["valid"] = assessment["valid"] and numerical_valid
    assessment["passed"] = assessment["passed"] and numerical_valid
    if not numerical_valid:
        assessment["core_score"] = 0.0
    assessment["metrics"] = {field: metrics[field] for field in METRIC_FIELDS}
    assessment["max_numerical_error_eh"] = float(max(errors))
    return assessment


def evaluate(candidate, uniforms):
    model.decode_witness(candidate)
    directions = np.array(uniforms, dtype=float)
    if directions.ndim != 2 or directions.shape[1] != 42 or not len(directions):
        raise ValueError("training directions must have shape (positive count, 42)")
    nominal = evaluate_case(candidate)
    cases = [evaluate_case(perturb(candidate, row)) for row in directions]
    successes = sum(case["passed"] for case in cases)
    fraction = successes / len(cases)
    required = math.ceil(SPEC["min_success_fraction"] * len(cases))
    valid = nominal["valid"] and all(case["numerical_valid"] for case in cases)
    nominal_score = nominal["core_score"]
    robust_score = min(1.0, fraction / SPEC["min_success_fraction"])
    passed = valid and nominal["passed"] and successes >= required
    failures = collections.Counter(group + "." + key for case in cases for group in ("admissibility", "witness_checks") for key, value in case.get(group, {}).items() if not value)
    return {
        "diagnostic_only": True,
        "official_hidden_assay": False,
        "valid": valid,
        "passed": passed,
        "reason": "public training assay passes" if passed else "public training diagnostic does not meet all conditions",
        "core_score": (nominal_score + robust_score) / 2 if valid else 0.0,
        "worst_family_score": min(nominal_score, robust_score) if valid else 0.0,
        "family_scores": {"nominal": nominal_score, "perturbed_assay": robust_score},
        "nominal": nominal,
        "perturbed_assay": {
            "case_count": len(cases),
            "required_successes": required,
            "successes": successes,
            "success_fraction": fraction,
            "physically_valid_cases": sum(case["valid"] for case in cases),
            "failure_counts_nonexclusive": dict(failures),
            "metric_ranges": {field: {"min": min(case["metrics"][field] for case in cases), "max": max(case["metrics"][field] for case in cases)} for field in METRIC_FIELDS},
            "max_numerical_error_eh": max(case["max_numerical_error_eh"] for case in cases),
        },
    }
