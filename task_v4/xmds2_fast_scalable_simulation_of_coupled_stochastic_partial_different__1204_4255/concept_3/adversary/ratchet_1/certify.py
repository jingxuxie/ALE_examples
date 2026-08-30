import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from field_control import evolve, fidelities, prolong, read_json, references, state_distance, validate_artifact


def audit(cases, artifact, protocol):
    splines, certificate = validate_artifact(artifact, protocol)
    policy = protocol["audit"]
    states, scores, diagnostics = [], [], []
    references_by_shape = {}
    maximum_residual = 0.0
    for shape, timestep in ((tuple(policy["spatial_grid"]), policy["dt"]), (tuple(policy["refined_grid"]), policy["dt"]), (tuple(policy["refined_grid"]), policy["refined_dt"])):
        if shape not in references_by_shape:
            references_by_shape[shape] = references(cases, shape, HERE / "reference_cache")
        initial, target, residual = references_by_shape[shape]
        maximum_residual = max(maximum_residual, residual)
        state, diagnostic = evolve(splines, cases, shape, timestep, initial)
        states.append(state)
        scores.append(fidelities(state, target, shape))
        diagnostics.append(diagnostic)
    allowance = 2 * (np.abs(scores[0] - scores[1]) + np.abs(scores[1] - scores[2])) + policy["fidelity_allowance"]
    space_distance = state_distance(prolong(states[0], tuple(policy["refined_grid"])), states[1], tuple(policy["refined_grid"]))
    time_distance = state_distance(states[1], states[2], tuple(policy["refined_grid"]))
    results = []
    for index, case in enumerate(cases):
        measures = {"max_allowance": float(allowance[index]), "max_state_distance": float(max(space_distance[index], time_distance[index])), "max_reference_residual": maximum_residual}
        for key in ("norm_error", "boundary_mass", "spectral_tail"):
            measures["max_" + key] = float(max(diagnostic[key][index] for diagnostic in diagnostics))
        failures = [key for key, value in measures.items() if not np.isfinite(value) or value > policy[key]]
        results.append({"case": case, "valid": not failures, "reason": "numerically_certified" if not failures else ",".join(failures), "raw_fidelity": float(scores[2][index]), "audited_fidelity": float(max(0.0, scores[2][index] - allowance[index])), "audit_values": measures, "level_fidelities": [float(level[index]) for level in scores]})
    return results, states[2]


def main():
    started = time.perf_counter()
    protocol = read_json(ROOT / "evaluator/hidden/protocol.json")
    artifact = read_json(ROOT / "attempts/v_2/control.json")
    cases = read_json(HERE / "certification_cases.json")
    results, fine_states = audit(cases, artifact, protocol)
    (HERE / "certified_cases.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    ordered = sorted(range(len(results)), key=lambda index: results[index]["audited_fidelity"])
    strong = [index for index in ordered if results[index]["valid"]][:3]
    boundary = sorted(range(len(results)), key=lambda index: results[index]["audit_values"]["max_boundary_mass"], reverse=True)[:2]
    selected = list(dict.fromkeys(strong + boundary))
    selected_cases = [cases[index] for index in selected]
    initial, target, residual = references(selected_cases, (160, 80), HERE / "reference_cache")
    splines, certificate = validate_artifact(artifact, protocol)
    extra_state, extra_diagnostic = evolve(splines, selected_cases, (160, 80), 0.0025, initial)
    extra_scores = fidelities(extra_state, target, (160, 80))
    distance = state_distance(prolong(fine_states[selected], (160, 80)), extra_state, (160, 80))
    extra = []
    for offset, index in enumerate(selected):
        extra.append({"case": cases[index], "purpose": [label for label, members in (("strong_fidelity_failure", strong), ("boundary_guard_check", boundary)) if index in members], "grid": [160, 80], "dt": 0.0025, "fidelity": float(extra_scores[offset]), "fidelity_difference_from_frozen_C": float(abs(extra_scores[offset] - results[index]["raw_fidelity"])), "state_distance_from_frozen_C": float(distance[offset]), "reference_residual": residual, "boundary_mass": float(extra_diagnostic["boundary_mass"][offset]), "norm_error": float(extra_diagnostic["norm_error"][offset]), "spectral_tail": float(extra_diagnostic["spectral_tail"][offset])})
    report = {"status": "complete", "checked_cases": len(cases), "certified_fidelity_failures": sum(entry["valid"] and entry["audited_fidelity"] < 0.98 for entry in results), "numerical_failures": sum(not entry["valid"] for entry in results), "max_reference_residual": max(entry["audit_values"]["max_reference_residual"] for entry in results), "extra_refinement": extra, "runtime_seconds": time.perf_counter() - started}
    (HERE / "certification_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
