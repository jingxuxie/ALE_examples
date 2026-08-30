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
    assert len(members) == 37
    assert len({member["name"] for member in members}) == 37
    corners = [member for member in members if member["group"] == "corner"]
    assert {tuple(member["coordinates"]) for member in corners} == set(itertools.product((-1, 1), repeat=5))
    assert sum(member["group"] == "legacy" for member in members) == 5
    assert sum(member["group"] == "interior" for member in members) == 0
    assert protocol["limits"] == {"certificate": 1e-4, "tail_mass": 0.02, "mass_drift": 2e-5, "energy_drift": 2e-4}
    assert protocol["target"]["minimum_conservative_density_gap"] == 0.3
    assert protocol["resources"]["evaluation_wall_seconds"] == 660
    assert protocol["resources"]["evaluation_cpu_seconds"] == 400
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
    assert result["valid"] and result["passed"] and result["complete_assessment"] and counts[0] == 37
    assert result["core_score"] == result["worst_family_score"] == 1.0
    counts[0] = 0

    def late_failure(member):
        report = successful(member)
        if counts[0] == 37:
            report.update(passed=False, family_score=0.4)
        return report

    search_api.assess_member = late_failure
    result = search_api.assess(parameters)
    assert result["valid"] and not result["passed"] and result["complete_assessment"]
    assert result["core_score"] == result["worst_family_score"] == 0.0
    assert result["observed_continuous_score"] == 0.4
    assert result["group_scores"]["corner"] == 0.0 and counts[0] == 37
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
    assert result["evaluated_family_members"] == 1 and len(result["skipped_members"]) == 36
    search_api.assess_member = original
    search_api.certificate_screen = original_screen
    guards = search_api.certificate_screen(parameters)
    assert guards["nominal"]["guard_passed"]
    expected = json.loads((ROOT / "participant/input/protocol.json").read_text())
    assert expected == json.loads((ROOT / "evaluator/hidden/protocol.json").read_text())
    assert (ROOT / "participant/workspace/search_api.py").read_bytes() == (ROOT / "evaluator/hidden/search_api.py").read_bytes()
    assert (ROOT / "participant/workspace/simulator.py").read_bytes() == (ROOT / "evaluator/hidden/simulator.py").read_bytes()
    report = {"passed": True, "checks": ["complete_32_corner_cartesian_design", "legacy_and_interior_counts", "unchanged_scalar_limits", "explicit_660_400_resource_budget", "baseline_byte_identity", "full_37_member_acceptance", "last_member_failure_not_skipped", "unresolved_reference_fails_closed", "certified_early_rejection_exact_binary_score", "cheap_guard_api", "public_frozen_byte_identity"], "nominal_guard_metrics": guards["nominal"]}
    (ROOT / "adversary/contract_controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
