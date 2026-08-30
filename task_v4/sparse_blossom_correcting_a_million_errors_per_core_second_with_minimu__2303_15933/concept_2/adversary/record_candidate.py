import hashlib
import json
import math
from pathlib import Path


PRIVATE = Path(__file__).resolve().parent


def main():
    report = json.loads((PRIVATE / "stress_report.json").read_text())
    artifact = json.loads((PRIVATE / "known_witness.json").read_text())
    assert report["artifact_sha256"] == hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest()
    audit = json.loads((PRIVATE / "stress_audit_report.json").read_text())
    assert audit["passed"] and report["independent_checks_performed"]
    cases = [case for case in report["cases"] if case["amplitude"] == 0.02]
    assert len(cases) == 338
    bounds = {metric: min(case["metrics"]["certified"][metric] for case in cases) for metric in ("gap", "posterior", "mass")}
    guard = {"gap": 0.9, "posterior": 0.84, "mass": 0.000017}
    local_score = min(bounds["gap"] / guard["gap"], math.log(bounds["posterior"] / (1 - bounds["posterior"])) / math.log(guard["posterior"] / (1 - guard["posterior"])), bounds["mass"] / guard["mass"])
    assert local_score > 1
    proposal = {"status": "PRIVATE_UNFROZEN_HYPOTHESIS_ONLY", "not_a_new_generation": True,
                "requires_actual_champion_assessment_before_selection": True,
                "nominal_targets_unchanged": report["policy"]["existing_targets_diagnostic_only"],
                "additional_condition": {"local_amplitude": 0.02, "profiles": len(cases),
                    "families": sorted({case["family"] for case in cases}), "seed": report["seed"],
                    "random_fields_per_family": report["random_fields_per_family"],
                    "noise_budget_preserving": True, "global_interval": [0.95, 1.05],
                    "guard_targets": guard, "entire_local_box_claimed": False},
                "known_feasibility": {"artifact": "known_witness.json", "certified_local_bounds": bounds,
                    "local_guard_score": local_score, "nominal_score": report["cases"][0]["metrics"]["certified_score"]},
                "caveat": "Feasible for this finite declared suite, not a proof over the full local uncertainty box. Do not select or freeze this ratchet before testing the actual champion."}
    (PRIVATE / "candidate_condition.json").write_text(json.dumps(proposal, indent=2) + "\n")
    (PRIVATE / "RATCHET_CANDIDATE.md").write_text(
        "# Private, unfrozen continuation hypothesis\n\n"
        "This is NOT a task generation, threshold freeze, or instruction for either running agent.\n\n"
        "A scientifically coherent additional condition is: retain the original nominal\n"
        "targets exactly, and require the 338 explicitly declared noise-budget-preserving\n"
        "local 2% profiles to certify gap >= 0.90, opposite posterior >= 0.84, and\n"
        "syndrome probability >= 0.000017 throughout global scales [0.95,1.05].\n"
        "The profile list comprises 82 row/column/quadrant/patch fields and two seeded\n"
        "families of 128 fields each. A future task would have to publish the profile\n"
        "construction, seed, and certificate. No claim is made for all local fields.\n\n"
        f"The existing private known witness certifies {bounds['gap']:.12g},\n"
        f"{bounds['posterior']:.12g}, and {bounds['mass']:.12g}, respectively;\n"
        f"local guard score {local_score:.12g}. Its original nominal pass is retained.\n"
        "No additional optimized nominal witness was needed or created.\n\n"
        "The strongest observed genuine instability is erosion of the weight-gap\n"
        "margin, not loss of entropy inversion: at 5% local calibration the exact\n"
        "gap falls to 0.814943376968 while the opposite posterior is 0.886996248818.\n"
        "Even 2% perturbations violate the original pointwise gap target for some\n"
        "profiles. No sampled posterior or mass target failure was found; their\n"
        "certificate failures must not be misrepresented as physical failures.\n\n"
        "Test the actual champion before selecting any continuation. This condition\n"
        "may not reject a strong champion; difficulty is unmeasured. The known design\n"
        "certifies basic inversion for all 677 tested profiles, so this sidecar is\n"
        "evidence of calibration-margin fragility, not wholesale decoder failure.\n\n"
        "## Reproduction from concept_2\n\n"
        "```bash\nOPENBLAS_NUM_THREADS=1 /usr/bin/python3 -B adversary/stress.py /path/to/witness.json\n"
        "/usr/bin/python3 -B adversary/test_stress.py\n```\n\n"
        "Use distinct `--output adversary/<name>.json --summary adversary/<name>.md`\n"
        "for a champion replay; `--skip-independent` is exploration-only and explicitly\n"
        "disables the generic-DP checks. The audit and candidate recorder are regressions\n"
        "for the saved known-witness report, not arbitrary champion reports.\n")
    print(json.dumps({"unfrozen": True, "local_guard_score": local_score, "known_bounds": bounds}, indent=2))


if __name__ == "__main__":
    main()
