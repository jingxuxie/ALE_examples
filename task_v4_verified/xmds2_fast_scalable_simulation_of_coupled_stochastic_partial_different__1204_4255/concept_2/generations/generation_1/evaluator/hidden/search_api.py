import json
import math
from pathlib import Path

import numpy as np

from simulator import diagnostics, field_distance, independent, integrate, observable_distance, quick


PROTOCOL_PATH = Path(__file__).resolve().parents[1] / "input" / "protocol.json"
if not PROTOCOL_PATH.exists():
    PROTOCOL_PATH = Path(__file__).with_name("protocol.json")
PROTOCOL = json.loads(PROTOCOL_PATH.read_text())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON number")


def parse_submission(text):
    payload = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if type(payload) is not dict or set(payload) != {"schema_version", "parameters"}:
        raise ValueError("expected exactly schema_version and parameters")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    parameters = payload["parameters"]
    bounds = PROTOCOL["parameter_bounds"]
    if type(parameters) is not dict or set(parameters) != set(bounds):
        raise ValueError("parameter names do not match protocol")
    result = {}
    for name, (lower, upper) in bounds.items():
        value = parameters[name]
        if type(value) not in (int, float):
            raise ValueError("parameter must be a real JSON number: " + name)
        if not lower <= value <= upper:
            raise ValueError("parameter outside allowed range: " + name)
        if not math.isfinite(value):
            raise ValueError("parameter is not finite: " + name)
        result[name] = float(value)
    return result


def family(parameters):
    for member in PROTOCOL["family"]:
        modified = dict(parameters)
        for name, factor in member["multiply"].items():
            modified[name] *= factor
        for name, offset in member["add"].items():
            modified[name] += offset
        yield member["name"], modified


def reference(parameters):
    settings = PROTOCOL["reference"]
    coarse = integrate(parameters, settings["base_grid"], settings["base_steps"])
    temporal = integrate(parameters, settings["base_grid"], settings["fine_steps"])
    spatial = integrate(parameters, settings["space_grid"], settings["fine_steps"])
    other, evaluations = independent(parameters, settings["base_grid"])
    differences = {}
    for name, first, second in (
        ("temporal", coarse, temporal), ("spatial", temporal, spatial),
        ("independent", temporal, other),
    ):
        differences[name + "_field_delta"] = float(np.max(field_distance(first, second)))
        differences[name + "_observable_delta"] = float(np.max(observable_distance(first, second)))
    field_uncertainty = 4 * sum(value for name, value in differences.items() if name.endswith("_field_delta")) + 1e-10
    observable_uncertainty = 4 * sum(value for name, value in differences.items() if name.endswith("_observable_delta")) + 1e-10
    invariant_checks = [diagnostics(parameters, state) for state in (coarse, temporal, spatial, other)]
    reference_diagnostics = {
        "mass_drift": max(item["mass_drift"] for item in invariant_checks),
        "energy_drift": max(item["energy_drift"] for item in invariant_checks),
        "tail_mass": invariant_checks[2]["tail_mass"],
    }
    resolved = (
        field_uncertainty <= settings["maximum_field_uncertainty"]
        and observable_uncertainty <= settings["maximum_observable_uncertainty"]
        and reference_diagnostics["tail_mass"] <= settings["maximum_reference_tail"]
        and reference_diagnostics["mass_drift"] <= PROTOCOL["limits"]["mass_drift"]
        and reference_diagnostics["energy_drift"] <= PROTOCOL["limits"]["energy_drift"]
    )
    return spatial, {
        **differences, "field_uncertainty": field_uncertainty,
        "observable_uncertainty": observable_uncertainty,
        "diagnostics": reference_diagnostics, "resolved": bool(resolved),
        "independent_rhs_evaluations": evaluations,
    }


def assess_member(parameters):
    settings = PROTOCOL["method_under_test"]
    coarse = integrate(parameters, settings["grid"], settings["coarse_steps"])
    fine = integrate(parameters, settings["grid"], settings["fine_steps"])
    certificate = field_distance(coarse, fine)
    coarse_diagnostics = diagnostics(parameters, coarse)
    fine_diagnostics = diagnostics(parameters, fine)
    metrics = {
        "certificate": float(np.max(certificate)),
        "tail_mass": fine_diagnostics["tail_mass"],
        "mass_drift": max(coarse_diagnostics["mass_drift"], fine_diagnostics["mass_drift"]),
        "energy_drift": max(coarse_diagnostics["energy_drift"], fine_diagnostics["energy_drift"]),
    }
    reference_state, reference_report = reference(parameters)
    gaps = observable_distance(fine, reference_state)
    target = PROTOCOL["target"]["minimum_conservative_density_gap"]
    selected = PROTOCOL["scored_observation_indices"]
    conservative_gap = max(0.0, float(np.min(gaps[selected])) - reference_report["observable_uncertainty"])
    guard_factor = min([1.0] + [limit / max(metrics[name], 1e-300) for name, limit in PROTOCOL["limits"].items()])
    guard_passed = all(metrics[name] <= limit for name, limit in PROTOCOL["limits"].items())
    resolved = reference_report["resolved"]
    return {
        **metrics, "certificate_by_time": certificate.tolist(),
        "density_gap_by_time": gaps.tolist(), "conservative_density_gap": conservative_gap,
        "guard_factor": guard_factor, "guard_passed": guard_passed,
        "family_score": min(1.0, conservative_gap / target) * guard_factor if resolved else 0.0,
        "passed": bool(resolved and guard_passed and conservative_gap >= target),
        "reference": reference_report,
    }


def assess(parameters):
    reports = []
    for name, member in family(parameters):
        reports.append({"name": name, **assess_member(member)})
    valid = all(report["reference"]["resolved"] for report in reports)
    passed = valid and all(report["passed"] for report in reports)
    score = min(report["family_score"] for report in reports) if valid else 0.0
    if not valid:
        reason = "reference_not_resolved"
    elif passed:
        reason = "robust_false_convergence_target_met"
    elif not all(report["guard_passed"] for report in reports):
        reason = "certificate_or_diagnostic_limit_failed"
    else:
        reason = "conservative_density_gap_below_target"
    return {
        "protocol_id": PROTOCOL["protocol_id"], "core_score": score,
        "worst_family_score": score, "valid": valid, "passed": passed,
        "reason": reason, "family": reports,
    }


def screen(parameters, all_members=False):
    members = family(parameters) if all_members else [("nominal", parameters)]
    return {name: quick(member) for name, member in members}
