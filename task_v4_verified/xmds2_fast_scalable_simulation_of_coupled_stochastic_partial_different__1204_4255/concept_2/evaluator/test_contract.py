import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
import search_api


def main():
    protocol = search_api.PROTOCOL
    members = protocol["family"]
    assert len(members) == 69
    assert len({member["name"] for member in members}) == 69
    corners = [member for member in members if member["group"] == "corner"]
    assert {tuple(member["coordinates"]) for member in corners} == set(itertools.product((-1, 1), repeat=5))
    assert sum(member["group"] == "legacy" for member in members) == 5
    assert sum(member["group"] == "interior" for member in members) == 0
    assert protocol["limits"] == {"certificate": 1e-4, "tail_mass": 0.02, "mass_drift": 2e-5, "energy_drift": 2e-4}
    assert protocol["target"]["minimum_conservative_density_gap"] == 0.3
    assert protocol["resources"]["evaluation_wall_seconds"] == 1500
    assert protocol["resources"]["evaluation_cpu_seconds"] == 900
    predecessor = json.loads((ROOT / "evaluator/hidden/predecessor_protocol.json").read_text())
    assert members[:37] == predecessor["family"]
    for name in ("schema", "parameter_bounds", "equation", "initial_condition", "method_under_test", "observation_fractions", "scored_observation_indices", "observable", "family_rule", "limits", "diagnostics"):
        assert protocol[name] == predecessor[name], name
    for name, value in predecessor["reference"].items():
        if name != "evaluation_pruning":
            assert protocol["reference"][name] == value, name
    fraction = [tuple(member["coordinates"]) for member in members if member["group"] == "joint_preparation"]
    assert len(fraction) == 32
    assert set(fraction) == {point for point in itertools.product((-1, 1), repeat=6) if sum(value == -1 for value in point) % 2 == 0}
    for omitted in range(6):
        projections = {tuple(value for index, value in enumerate(point) if index != omitted) for point in fraction}
        assert projections == set(itertools.product((-1, 1), repeat=5))
    assert protocol["generation"] == 3 and protocol["resources"]["development_cpu_seconds"] == 3600
    parameters = search_api.parse_submission((ROOT / "participant/baseline/champion.json").read_text())
    assert (ROOT / "attempts/baseline.json").read_bytes() == (ROOT / "participant/baseline/champion.json").read_bytes()
    original = search_api.assess_member
    original_screen = search_api.certificate_screen
    search_api.certificate_screen = lambda parameters, all_members=False: {member["name"]: {"certificate": 1e-5, "tail_mass": 0.001, "mass_drift": 1e-8, "energy_drift": 1e-7, "guard_passed": True} for member in members}
    counts = [0]

    def successful(member):
        counts[0] += 1
        return {"reference": {"resolved": True}, "passed": True, "family_score": 1.0, "guard_passed": True}

    search_api.assess_member = successful
    result = search_api.assess(parameters)
    assert result["valid"] and result["passed"] and result["complete_assessment"] and counts[0] == 69
    assert result["core_score"] == result["worst_family_score"] == 1.0
    counts[0] = 0

    def late_failure(member):
        report = successful(member)
        if counts[0] == 69:
            report.update(passed=False, family_score=0.4)
        return report

    search_api.assess_member = late_failure
    result = search_api.assess(parameters)
    assert result["valid"] and not result["passed"] and result["complete_assessment"]
    assert result["core_score"] == result["worst_family_score"] == 0.0
    assert result["observed_continuous_score"] == 0.4
    assert result["group_scores"]["joint_preparation"] == 0.0 and counts[0] == 69
    counts[0] = 0

    def unresolved(member):
        report = successful(member)
        if counts[0] == 7:
            report.update(reference={"resolved": False}, passed=False, family_score=0.0)
        return report

    search_api.assess_member = unresolved
    result = search_api.assess(parameters)
    assert not result["valid"] and not result["passed"] and not result["complete_assessment"]
    assert result["core_score"] == result["worst_family_score"] == 0.0
    assert result["evaluated_family_members"] == counts[0] == 7
    counts[0] = 0

    def early_failure(member):
        report = successful(member)
        report.update(passed=False, family_score=0.75)
        return report

    search_api.assess_member = early_failure
    result = search_api.assess(parameters)
    assert result["valid"] and not result["passed"] and not result["complete_assessment"]
    assert result["core_score"] == 0 and result["observed_continuous_score"] == 0.75
    assert result["evaluated_family_members"] == 1 and len(result["skipped_members"]) == 68
    counts[0] = 0
    result = search_api.assess(parameters, exhaustive=True)
    assert result["valid"] and not result["passed"] and result["complete_assessment"]
    assert result["evaluated_family_members"] == counts[0] == 69 and not result["skipped_members"]
    assert result["reason"] == "certified_family_threshold_failure" and result["exhaustive"]
    counts[0] = 0
    search_api.assess_member = unresolved
    result = search_api.assess(parameters, exhaustive=True)
    assert not result["valid"] and not result["passed"] and counts[0] == 7
    assert result["reason"] == "reference_not_resolved"
    search_api.assess_member = original
    search_api.certificate_screen = original_screen
    guards = search_api.certificate_screen(parameters)
    assert guards["nominal"]["guard_passed"]
    expected = json.loads((ROOT / "participant/input/protocol.json").read_text())
    assert expected == json.loads((ROOT / "evaluator/hidden/protocol.json").read_text())
    assert (ROOT / "participant/workspace/search_api.py").read_bytes() == (ROOT / "evaluator/hidden/search_api.py").read_bytes()
    assert (ROOT / "participant/workspace/simulator.py").read_bytes() == (ROOT / "evaluator/hidden/simulator.py").read_bytes()
    report = {"passed": True, "checks": ["complete_32_corner_cartesian_design", "legacy_and_interior_counts", "unchanged_scalar_limits", "explicit_1500_900_resource_budget", "baseline_byte_identity", "full_69_member_acceptance", "last_member_failure_not_skipped", "unresolved_reference_fails_closed", "certified_early_rejection_exact_binary_score", "cheap_guard_api", "public_frozen_byte_identity", "all_37_predecessor_members_retained", "six_factor_parity_fixed_before_measurement", "every_five_factor_projection_complete", "unchanged_equations_admissibility_reference_thresholds", "exhaustive_failure_visits_all_69", "exhaustive_unresolved_still_fails_closed"], "nominal_guard_metrics": guards["nominal"]}
    (ROOT / "adversary/contract_controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
