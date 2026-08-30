import collections
import json
import math
from pathlib import Path

import numpy as np

import model


INPUT = Path(__file__).resolve().parents[1] / "input"
SPEC = json.loads((INPUT / "assay_spec.json").read_text())
FAMILIES = ("vv", "full")
DIMENSIONS = {"vv": 42, "full": 100}
EDGES = [(source, destination) for source in range(10) for destination in range(source + 1, 10)]
METRIC_FIELDS = ("full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "tail_to_parent_ratio", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh")
PHYSICAL_FLAGS = ("hf_weight", "spectral_gap", "diagonal_margin")


def training_uniforms(seed=None, samples=None):
    if seed is None and samples is None:
        stored = json.loads((INPUT / "training_uniforms.json").read_text())
        return {family: np.asarray(stored["families"][family], dtype=float) for family in FAMILIES}
    count = SPEC["public_training_cases"] if samples is None else samples
    selected_seed = SPEC["public_training_seed"] if seed is None else seed
    if type(count) is not int or not 1 <= count <= 512:
        raise ValueError("public samples per family must be between 1 and 512")
    if type(selected_seed) is not int or selected_seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    streams = np.random.SeedSequence(selected_seed).spawn(2)
    return {family: np.random.Generator(np.random.PCG64(stream)).random((count, DIMENSIONS[family]))
            for family, stream in zip(FAMILIES, streams)}


def perturb(candidate, uniforms, family):
    if family not in FAMILIES:
        raise ValueError("family must be vv or full")
    directions = np.asarray(uniforms, dtype=float)
    if directions.shape != (DIMENSIONS[family],) or not np.all(np.isfinite(directions)) or np.any(directions < 0) or np.any(directions >= 1):
        raise ValueError("directions have wrong shape or are outside [0,1)")
    energies, hopping, density = model.full_coefficients(candidate)
    radius = SPEC["delta_eh"]
    cursor = 0
    if family == "full":
        for orbital in range(10):
            energies[orbital] += radius * (2.0 * directions[cursor] - 1.0)
            cursor += 1
    for matrix, bound in ((hopping, model.TARGET["hopping_bound_eh"]), (density, model.TARGET["density_bound_eh"])):
        for source, destination in EDGES:
            if family == "vv" and source < 3:
                continue
            lower = max(-bound, matrix[source, destination] - radius)
            upper = min(bound, matrix[source, destination] + radius)
            value = lower + directions[cursor] * (upper - lower)
            matrix[source, destination] = matrix[destination, source] = value
            cursor += 1
    return model.validate_coefficients((energies, hopping, density))


def evaluate_case(coefficients):
    metrics = model.compute_coefficients(coefficients, complete=True)
    assessment = model.score(metrics)
    energies = metrics["subset_energies_eh"]
    variational = max([0.0] + [energies[str(mask | (1 << index))] - energies[str(mask)]
                             for mask in range(128) for index in range(7) if not mask & (1 << index)])
    errors = [metrics["eigen_residual_eh"], metrics["closure_error_eh"],
              abs(energies["127"] - metrics["full_energy_eh"]), variational]
    numerical_valid = all(math.isfinite(value) and value <= model.TARGET["numerical_check_eh"] for value in errors)
    assessment["numerical_valid"] = numerical_valid
    assessment["valid"] = assessment["valid"] and numerical_valid
    assessment["passed"] = assessment["passed"] and numerical_valid
    if not numerical_valid:
        assessment["core_score"] = 0.0
    assessment["metrics"] = {field: metrics[field] for field in METRIC_FIELDS}
    assessment["max_numerical_error_eh"] = float(max(errors))
    return assessment


def summarize(cases):
    clusters = collections.Counter()
    failures = collections.Counter()
    physical_failures = collections.Counter()
    for case in cases:
        labels = []
        if not case["numerical_valid"]:
            labels.append("numerical")
        physical = [name for name in PHYSICAL_FLAGS if not case["admissibility"][name]]
        physical_failures.update(physical)
        if physical:
            labels.append("physical")
        labels += [label for name, label in (("all_triples_small", "parents"), ("material_tail", "material_tail"), ("large_ratio", "ratio"))
                   if not case["witness_checks"][name]]
        failures.update(labels)
        clusters["+".join(labels) if labels else "pass"] += 1
    successes = sum(case["passed"] for case in cases)
    return {
        "case_count": len(cases), "required_successes": math.ceil(SPEC["min_success_fraction"] * len(cases)),
        "successes": successes, "success_fraction": successes / len(cases),
        "physically_valid_cases": sum(all(case["admissibility"][name] for name in PHYSICAL_FLAGS) for case in cases),
        "numerically_valid_cases": sum(case["numerical_valid"] for case in cases),
        "failure_counts_nonexclusive": dict(failures), "failure_clusters": dict(clusters),
        "physical_failure_counts": dict(physical_failures),
        "metric_ranges": {field: {"min": min(case["metrics"][field] for case in cases), "max": max(case["metrics"][field] for case in cases)} for field in METRIC_FIELDS},
        "minimum_individual_nominal_score": min(case["core_score"] for case in cases),
        "max_numerical_error_eh": max(case["max_numerical_error_eh"] for case in cases),
    }


def evaluate(candidate, uniforms):
    model.decode_witness(candidate)
    if not isinstance(uniforms, dict) or set(uniforms) != set(FAMILIES):
        raise ValueError("provide exactly vv and full direction pools")
    pools = {family: np.asarray(uniforms[family], dtype=float) for family in FAMILIES}
    for family, values in pools.items():
        if values.ndim != 2 or values.shape[1] != DIMENSIONS[family] or not len(values):
            raise ValueError("invalid training pool shape")
        if not np.all(np.isfinite(values)) or np.any(values < 0) or np.any(values >= 1):
            raise ValueError("training directions must be finite in [0,1)")
    nominal = evaluate_case(model.full_coefficients(candidate))
    cases = {family: [evaluate_case(perturb(candidate, row, family)) for row in pools[family]] for family in FAMILIES}
    reports = {family: summarize(cases[family]) for family in FAMILIES}
    valid = nominal["valid"] and all(case["numerical_valid"] for family in FAMILIES for case in cases[family])
    family_scores = {"nominal": nominal["core_score"]}
    family_scores.update({family: min(1.0, reports[family]["success_fraction"] / SPEC["min_success_fraction"]) for family in FAMILIES})
    passed = valid and nominal["passed"] and all(reports[family]["successes"] >= reports[family]["required_successes"] for family in FAMILIES)
    return {
        "diagnostic_only": True, "official_hidden_assay": False,
        "valid": valid, "passed": passed,
        "reason": "public two-family assay passes" if passed else "public diagnostic does not meet all conditions",
        "core_score": math.fsum(family_scores.values()) / 3 if valid else 0.0,
        "worst_family_score": min(family_scores.values()) if valid else 0.0,
        "family_scores": family_scores, "nominal": nominal, "robustness_families": reports,
    }
