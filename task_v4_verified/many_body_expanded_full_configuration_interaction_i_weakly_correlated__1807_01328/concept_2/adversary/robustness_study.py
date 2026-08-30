import collections
import datetime
import hashlib
import importlib.util
import json
import math
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "adversary"
MAGNITUDES = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2)
METHODS = ("raw_uniform", "box_conditioned_uniform", "stochastic_rounding")
SAMPLES = 20
SEED = 20260828
TIME_BUDGET_SECONDS = 120.0
EDGES = [(row, column) for row in range(7) for column in range(row + 1, 7)]
FIELDS = ("virtual_hopping", "virtual_density")
METRICS = ("max_abs_triple_eh", "tail_eh", "signed_tail_eh", "tail_to_parent_ratio", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh", "discarded_quadruples")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(manifest):
    actual = {relative: digest(ROOT / relative) for relative in manifest["files"]}
    differences = [relative for relative, expected in manifest["files"].items() if actual[relative] != expected]
    return dict(file_count=len(actual), matches_frozen_manifest=not differences, changed_paths=differences, sha256=actual)


def module_at(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def encode(values):
    candidate = {"schema_version": 1}
    for field_index, field in enumerate(FIELDS):
        matrix = [[0.0] * 7 for row in range(7)]
        for edge_index, (row, column) in enumerate(EDGES):
            matrix[row][column] = matrix[column][row] = float(values[field_index, edge_index])
        candidate[field] = matrix
    return candidate


def wilson_interval(passed, total):
    if not total:
        return None
    multiplier = 1.959963984540054
    proportion = passed / total
    denominator = 1 + multiplier ** 2 / total
    center = (proportion + multiplier ** 2 / (2 * total)) / denominator
    half_width = multiplier * math.sqrt(proportion * (1 - proportion) / total + multiplier ** 2 / (4 * total ** 2)) / denominator
    return [max(0.0, center - half_width), min(1.0, center + half_width)]


def perturbed(center, bounds, magnitude, method, generator):
    if method == "raw_uniform":
        return center + generator.uniform(-magnitude, magnitude, center.shape)
    if method == "box_conditioned_uniform":
        lower = np.maximum(center - magnitude, -bounds)
        upper = np.minimum(center + magnitude, bounds)
        return generator.uniform(lower, upper)
    digits = int(round(-math.log10(magnitude)))
    if method == "nearest_rounding":
        return np.array([[round(float(value), digits) for value in row] for row in center])
    lower_indices = np.floor(center / magnitude)
    upper_probability = np.clip(center / magnitude - lower_indices, 0.0, 1.0)
    rounded_indices = lower_indices + (generator.random(center.shape) < upper_probability)
    return np.array([[round(float(value) * magnitude, digits) for value in row] for row in rounded_indices])


def evaluate(values, center, bounds, scratch, verifier):
    payload = json.dumps(encode(values), allow_nan=False, separators=(",", ":")) + "\n"
    scratch.write_text(payload)
    difference = values - center
    failures = ["coefficient_bounds." + field for index, field in enumerate(FIELDS) if np.any(np.abs(values[index]) > bounds[index])]
    record = {
        "candidate_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "perturbation_linf_eh": float(np.max(np.abs(difference))),
        "perturbation_l2_eh": float(np.linalg.norm(difference)),
        "coefficient_bounds_valid": not failures,
    }
    started = time.perf_counter()
    try:
        parsed = verifier.read_candidate(scratch)
        metrics = verifier.calculate(*parsed)
        assessment = verifier.assess(metrics)
        record.update(valid=assessment["valid"], passed=assessment["passed"], core_score=assessment["core_score"], reason=assessment["reason"])
        for group in ("admissibility", "witness_checks"):
            failures.extend(group + "." + key for key, passed in assessment.get(group, {}).items() if not passed)
        record["metrics"] = {field: metrics[field] for field in METRICS}
        triples = {mask: value for mask, value in metrics["increments_eh"].items() if int(mask).bit_count() == 3}
        worst_mask = int(max(triples, key=lambda mask: abs(triples[mask])))
        record["worst_triple_mask"] = worst_mask
        record["worst_triple_orbitals"] = [index + 3 for index in range(7) if worst_mask & (1 << index)]
        record["max_numerical_check_error_eh"] = max(metrics[field] for field in ("eigen_residual_eh", "closure_error_eh", "variational_violation_eh", "full_solver_disagreement_eh"))
    except (ValueError, TypeError, OSError, OverflowError) as error:
        record.update(valid=False, passed=False, core_score=0.0, reason=str(error))
        if not failures:
            failures.append("input_validation")
    record["failures"] = failures
    record["evaluation_seconds"] = time.perf_counter() - started
    return record


def summarize(records, stochastic):
    passed = sum(record["passed"] for record in records)
    valid = sum(record["valid"] for record in records)
    total = len(records)
    summary = {
        "sample_count": total,
        "passed_count": passed,
        "valid_count": valid,
        "coefficient_bounds_valid_count": sum(record["coefficient_bounds_valid"] for record in records),
        "pass_rate": passed / total if total else None,
        "valid_rate": valid / total if total else None,
        "pass_rate_given_valid": passed / valid if valid else None,
        "wilson_95_pass_interval": wilson_interval(passed, total) if stochastic else None,
        "failure_counts_nonexclusive": dict(collections.Counter(failure for record in records for failure in record["failures"])),
        "unique_candidate_count": len({record["candidate_sha256"] for record in records}),
        "worst_triple_mask_counts": dict(collections.Counter(str(record["worst_triple_mask"]) for record in records if "worst_triple_mask" in record)),
    }
    summary["metric_quantiles"] = {}
    for field in METRICS:
        values = [record["metrics"][field] for record in records if "metrics" in record]
        if values:
            summary["metric_quantiles"][field] = dict(zip(("min", "p05", "median", "p95", "max"), map(float, np.quantile(values, [0, 0.05, 0.5, 0.95, 1]))))
    return summary


def main():
    started = time.perf_counter()
    manifest_path = ROOT / "evaluator/hidden/freeze.json"
    manifest = json.loads(manifest_path.read_text())
    before = audit(manifest)
    critical_differences = [relative for relative in before["changed_paths"] if relative != "participant/TASK.md"]
    if critical_differences:
        raise RuntimeError("scientific files differ before study: " + repr(critical_differences))
    verifier = module_at("frozen_private_verifier", "evaluator/hidden/verify.py")
    wrapper = module_at("frozen_evaluator_wrapper", "evaluator/evaluate.py")
    witness_path = PRIVATE / "known_witness.json"
    witness_hash = digest(witness_path)
    witness = json.loads(witness_path.read_text())
    center = np.array([[witness[field][row][column] for row, column in EDGES] for field in FIELDS])
    bounds = np.array([[verifier.TARGET["hopping_bound_eh"]], [verifier.TARGET["density_bound_eh"]]])
    report = {
        "schema_version": 1,
        "study": "private author witness perturbation and rounding robustness",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target_id": manifest["target_id"],
        "target_sha256": manifest["target_sha256"],
        "known_witness_sha256": witness_hash,
        "freeze_manifest_sha256": digest(manifest_path),
        "protocol": {
            "seed": SEED,
            "numpy_version": np.__version__,
            "magnitudes_eh": list(MAGNITUDES),
            "random_samples_per_method_per_magnitude": SAMPLES,
            "max_candidate_evaluations_including_control": 306,
            "max_additional_official_cli_cross_checks": 5,
            "max_total_numerical_evaluations": 311,
            "wall_budget_seconds": TIME_BUDGET_SECONDS,
            "random_stream": "independent PCG64 streams from SeedSequence([seed, magnitude_index, method_index, sample_index])",
            "coordinates": "42 upper-triangle entries, hopping followed by density; lexicographic orbital pairs; mirror exactly; always perturb original known witness, never cumulatively",
            "raw_uniform": "independent additive Uniform[-magnitude,+magnitude] per coordinate, no clipping or rejection-resampling; out-of-bound samples count as failures",
            "box_conditioned_uniform": "independent uniform values in intersection of [original-magnitude,original+magnitude] with each coefficient bound; conditional distribution, not clipping",
            "stochastic_rounding": "independent floor/ceiling rounding to the magnitude grid, with probability equal to fractional grid position; unbiased up to binary floating point",
            "nearest_rounding": "one deterministic round(value, decimal_digits) control per magnitude; nearest grid, ties to even; no probability interpretation",
            "numerics": "unchanged independent hidden parser, fermionic-bitmask Hamiltonian, all 128 subset energies, direct alternating increments, unchanged assess; no participant imports",
            "uncertainty": "Wilson 95% intervals are unadjusted marginal binomial intervals for random trials; 20/20 is not a universal guarantee",
            "failure_counts": "nonexclusive violated gates; diagnoses benchmark failure conditions, not unique causal attribution to coefficients",
        },
        "audit_before": before,
        "preexisting_manifest_differences": before["changed_paths"],
        "audit_note": "A pre-existing participant/TASK.md hash difference is recorded, not repaired. Every scientific target, model, and evaluator file must still match the original manifest; before/after hashes separately detect changes during this private study.",
        "coefficient_margin_eh": {field: float(bounds[index, 0] - np.max(np.abs(center[index]))) for index, field in enumerate(FIELDS)},
        "groups": [],
        "cli_cross_checks": [],
    }
    with tempfile.TemporaryDirectory(prefix=".robustness-", dir=PRIVATE) as directory:
        scratch = Path(directory) / "witness.json"
        report["unperturbed_control"] = evaluate(center, center, bounds, scratch, verifier)
        if not report["unperturbed_control"]["passed"]:
            raise RuntimeError("known witness no longer passes frozen verifier")
        print("Scientific-file audit and unperturbed witness pass; starting bounded study.", flush=True)
        for magnitude_index, magnitude in enumerate(MAGNITUDES):
            for method_index, method in enumerate(METHODS + ("nearest_rounding",)):
                records = []
                requested = 1 if method == "nearest_rounding" else SAMPLES
                for sample_index in range(requested):
                    if time.perf_counter() - started > TIME_BUDGET_SECONDS:
                        break
                    seed_components = [SEED, magnitude_index, method_index, sample_index]
                    generator = np.random.default_rng(np.random.SeedSequence(seed_components))
                    values = perturbed(center, bounds, magnitude, method, generator)
                    record = evaluate(values, center, bounds, scratch, verifier)
                    record.update(sample_index=sample_index, seed_components=seed_components if method != "nearest_rounding" else None)
                    records.append(record)
                    if method == "nearest_rounding":
                        official = wrapper.evaluate(scratch)
                        agreement = all(official[field] == record[field] for field in ("valid", "passed", "core_score"))
                        report["cli_cross_checks"].append(dict(magnitude_eh=magnitude, agrees=agreement, official=official))
                        if not agreement:
                            raise RuntimeError("official CLI assessment disagreement")
                group = dict(method=method, magnitude_eh=magnitude, requested_samples=requested, summary=summarize(records, method != "nearest_rounding"), samples=records)
                report["groups"].append(group)
                print(json.dumps(dict(method=method, magnitude_eh=magnitude, passed=group["summary"]["passed_count"], total=len(records), failures=group["summary"]["failure_counts_nonexclusive"])), flush=True)
    report["audit_after"] = audit(manifest)
    report["known_witness_unchanged"] = digest(witness_path) == witness_hash
    report["completed_samples"] = sum(group["summary"]["sample_count"] for group in report["groups"])
    report["complete"] = report["completed_samples"] == 305
    report["max_numerical_check_error_eh"] = max(record.get("max_numerical_check_error_eh", 0.0) for group in report["groups"] for record in group["samples"])
    report["runtime_seconds"] = time.perf_counter() - started
    report["peak_memory_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    report["conclusion_scope"] = "Local, distribution-specific robustness of the author fixture only. No new ratchet or acceptance threshold is applied; no fresh outcomes were consulted. All fresh integration and future benchmark design remain with main."
    report["frozen_files_unchanged_during_study"] = before["sha256"] == report["audit_after"]["sha256"]
    report["scientific_files_match_original_manifest"] = not [relative for relative in report["audit_after"]["changed_paths"] if relative != "participant/TASK.md"]
    destination = PRIVATE / "robustness.json"
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not report["frozen_files_unchanged_during_study"] or not report["known_witness_unchanged"]:
        raise RuntimeError("artifact audit changed during study; see robustness.json")
    print(json.dumps(dict(report=str(destination), complete=report["complete"], samples=report["completed_samples"], runtime_seconds=report["runtime_seconds"], frozen_files_unchanged_during_study=report["frozen_files_unchanged_during_study"])), flush=True)


if __name__ == "__main__":
    main()
