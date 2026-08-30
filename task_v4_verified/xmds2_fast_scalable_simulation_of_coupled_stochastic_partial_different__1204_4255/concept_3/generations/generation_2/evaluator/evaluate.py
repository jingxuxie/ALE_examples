import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

TRUSTED = Path(__file__).resolve().parent / "hidden"
sys.path.insert(0, str(TRUSTED))
from field_control import evolve, failure, fidelities, prolong, read_json, references, resource_score, state_distance, summarize, validate_artifact


def evaluate(artifact_path):
    started = time.perf_counter()
    try:
        protocol = read_json(TRUSTED / "protocol.json")
        cases = read_json(TRUSTED / "cases.json")
        artifact = read_json(artifact_path, protocol["artifact_max_bytes"])
        splines, control_diagnostics = validate_artifact(artifact, protocol)
        artifact_hash = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        policy = protocol["audit"]
        coarse_shape = tuple(policy["spatial_grid"])
        fine_shape = tuple(policy["refined_grid"])
        initial_coarse, target_coarse, residual_coarse = references(cases, coarse_shape, TRUSTED / "references")
        initial_fine, target_fine, residual_fine = references(cases, fine_shape, TRUSTED / "references")
        spatial, spatial_diagnostics = evolve(splines, cases, coarse_shape, policy["dt"], initial_coarse)
        temporal, temporal_diagnostics = evolve(splines, cases, fine_shape, policy["dt"], initial_fine)
        refined, refined_diagnostics = evolve(splines, cases, fine_shape, policy["refined_dt"], initial_fine)
        spatial_scores = fidelities(spatial, target_coarse, coarse_shape)
        temporal_scores = fidelities(temporal, target_fine, fine_shape)
        refined_scores = fidelities(refined, target_fine, fine_shape)
        spatial_difference = np.abs(spatial_scores - temporal_scores)
        temporal_difference = np.abs(temporal_scores - refined_scores)
        allowance = 2.0 * (spatial_difference + temporal_difference) + policy["fidelity_allowance"]
        lower_scores = np.clip(refined_scores - allowance, 0.0, 1.0)
        distance_time = state_distance(temporal, refined, fine_shape)
        distance_space = state_distance(prolong(spatial, fine_shape), temporal, fine_shape)
        diagnostics = {key: float(max(np.max(spatial_diagnostics[key]), np.max(temporal_diagnostics[key]), np.max(refined_diagnostics[key]))) for key in refined_diagnostics}
        audit_values = {"max_allowance": float(np.max(allowance)), "max_state_distance": float(max(np.max(distance_time), np.max(distance_space))), "max_norm_error": diagnostics["norm_error"], "max_boundary_mass": diagnostics["boundary_mass"], "max_spectral_tail": diagnostics["spectral_tail"], "max_reference_residual": max(residual_coarse, residual_fine)}
        if not all(np.isfinite(value) for value in audit_values.values()) or not np.all(np.isfinite(lower_scores)):
            raise ArithmeticError("nonfinite score or audit statistic")
        failed_audits = [key for key, value in audit_values.items() if value > policy[key]]
        result = summarize(lower_scores, cases, protocol)
        result["valid"] = not failed_audits
        result["artifact_canonical_sha256"] = artifact_hash
        result["passed"] = result["passed"] and result["valid"]
        result["reason"] = "passed" if result["passed"] else ("numerical_audit_failed: " + ",".join(failed_audits) if failed_audits else "fidelity_threshold_not_met")
        result.update({"protocol": protocol["protocol"], "runtime_seconds": time.perf_counter() - started, "runtime_score": min(1.0, protocol["evaluation_runtime_reference_seconds"] / max(time.perf_counter() - started, 1e-9)), "resource_score": resource_score(splines, protocol), "thresholds": protocol["thresholds"], "audits": audit_values, "control_diagnostics": control_diagnostics, "cases": [{"id": case["id"], "family": case["family"], "refined_fidelity": float(score), "allowance": float(error), "audited_fidelity": float(lower)} for case, score, error, lower in zip(cases, refined_scores, allowance, lower_scores)]})
        if failed_audits:
            result["uncertified_core_score"] = result["core_score"]
            result["core_score"] = 0.0
            result["worst_family_score"] = 0.0
            result["worst_case_score"] = 0.0
        return result
    except Exception as error:
        return failure(type(error).__name__ + ": " + str(error), time.perf_counter() - started)


def main():
    parser = argparse.ArgumentParser(description="Trusted artifact-only coherent GP splitter evaluator")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    result = evaluate(arguments.artifact)
    text = json.dumps(result, indent=2, allow_nan=False)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    print(text)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
