import argparse
import copy
import hashlib
import itertools
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_3"


def serialized(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("variable", choices=("population", "cross", "coupling"))
    parser.add_argument("width", type=float)
    arguments = parser.parse_args()
    records = json.loads((AUDIT / "preparation_verified.json").read_text())
    evidence = [item for item in records if item["variable"] == arguments.variable and item["width"] == arguments.width]
    controls = [item for item in evidence if item["kind"] == "single_axis"]
    failures = [item for item in evidence if item["canonical_fraction"] and item["assessment"]["reference"]["resolved"] and not item["assessment"]["passed"]]
    assert len(controls) == 2 and all(item["assessment"]["passed"] for item in controls)
    assert failures, "Staging requires a fully referenced failure in the preregistered fraction"
    assert not STAGE.exists(), "Do not overwrite an existing staged design"
    source_protocol = json.loads((ROOT / "participant/input/protocol.json").read_text())
    protocol = copy.deepcopy(source_protocol)
    protocol["protocol_id"] = "nonlinear_joint_preparation_v3"
    protocol["generation"] = 3
    operation = "add" if arguments.variable == "population" else "multiply"
    for index, point in enumerate(itertools.product((-1, 1), repeat=6)):
        if math.prod(point) != 1:
            continue
        multiply = {"nonlinearity": 1 + 0.02 * point[0], "duration": 1 + 0.02 * point[1]}
        add = {"a1": 0.01 * point[2], "a2": 0.01 * point[3], "relative_phase": 0.03 * point[4]}
        if operation == "add":
            add[arguments.variable] = arguments.width * point[5]
        else:
            multiply[arguments.variable] = 1 + arguments.width * point[5]
        protocol["family"].append({"name": "joint6_%02d" % index, "group": "joint_preparation", "coordinates": list(point), "multiply": multiply, "add": add})
    assert len(protocol["family"]) == 69
    for section in ("target", "reference"):
        for key, value in protocol[section].items():
            if isinstance(value, str):
                protocol[section][key] = value.replace("37", "69")
    protocol["target"]["definition"] = "For every one of the 69 explicit members, minimum density-observable gap at t/T=0.75,0.875,1 minus its validated observable uncertainty must be >=0.3; all unchanged certificate, tail, mass and energy limits must also hold. No undisclosed evaluation members."
    protocol["reference"]["evaluation_pruning"] += " Optional organizer/public --exhaustive disables threshold-failure pruning only, never unresolved-reference rejection, and does not change the target or score. This measures the full passing-path workload even for a failing input."
    protocol["resources"].update(evaluation_wall_seconds=1500, evaluation_cpu_seconds=900, wall_budget_rationale="All 69 members require full temporal, spatial and independent-method references on any passing submission. Generation-two passing runs used 283-286 CPU seconds for 37 members. The 900-CPU/1500-wall budget is calibrated with an exhaustive 69-member traversal before sealing; default certified early rejection is retained. One-hour development CPU allowance is unchanged.")
    protocol["uncertainty_design"] = {
        "coordinates": ["nonlinearity_calibration", "duration_calibration", "first_shape", "second_shape", "relative_phase", arguments.variable],
        "calibration_relative_half_width": 0.02,
        "shape_absolute_half_width": 0.01,
        "phase_absolute_half_width_radians": 0.03,
        "sixth_coordinate": {"parameter": arguments.variable, "operation": operation, "half_width": arguments.width},
        "construction": "Retain all 37 generation-two members exactly. Append the fixed product(signs)=+1 half-fraction of the six independent sign coordinates: 32 of the 64 six-factor corners, in lexicographic (-1,+1) order. Indices retain their full 64-corner index. Parity was specified before these failures were measured. Every projection onto any five coordinates is the complete 32-corner set, without claiming all 64 joint corners.",
        "claim_scope": "The target concerns exactly these 69 listed members, not the continuous box or the complementary half-fraction. All transformations, widths and members are public. No random or hidden perturbation is used for grading.",
        "physical_interpretation": "Independent small calibration, smooth-shape, phase and preparation uncertainty. The sixth coordinate changes an existing physical parameter, not the equations, spectral support, numerical solver or thresholds.",
        "bounds": "Apply all listed perturbations literally to the admissible base point, without clipping, renormalizing parameter values or wrapping phases. Initial fields retain the unchanged unit total population normalization and |k|<=3 support."
    }
    protocol["interface"]["baseline_description"] = "Copies the officially verified generation-two v_3 champion byte-for-byte. It is the previous generation's strongest minimum normalized margin, not a generation-three solution. No privately optimized witness is supplied."
    protocol["interface"]["exhaustive_evaluate"] = "/usr/bin/python3 evaluator/evaluate.py --submission attempts/baseline.json --exhaustive --output attempts/baseline.exhaustive.json"
    protocol["interface"]["exhaustive_public_check"] = protocol["interface"]["full_public_check"] + " --exhaustive"
    protocol["interface"]["output"] += " exhaustive reports whether threshold-failure pruning was disabled; score 1 still requires all 69 references and conditions."
    files = {}
    files["evaluator/hidden/predecessor_protocol.json"] = serialized(source_protocol)
    for relative in ("participant/workspace/simulator.py", "evaluator/hidden/simulator.py", "adversary/test_controls.py"):
        files[relative] = (ROOT / relative).read_text()
    api = (ROOT / "participant/workspace/search_api.py").read_text()
    api = api.replace("def assess(parameters):", "def assess(parameters, exhaustive=False):")
    api = api.replace('reason = "certified_family_threshold_failure"\n            break', 'reason = "certified_family_threshold_failure"\n            if not exhaustive:\n                break')
    api = api.replace('"complete_assessment": complete,', '"complete_assessment": complete, "exhaustive": bool(exhaustive),')
    files["participant/workspace/search_api.py"] = api
    files["evaluator/hidden/search_api.py"] = api
    for relative in ("participant/input/protocol.json", "evaluator/hidden/protocol.json"):
        files[relative] = serialized(protocol)
    wrapper = (ROOT / "evaluator/evaluate.py").read_text()
    wrapper = wrapper.replace('parser.add_argument("--output")', 'parser.add_argument("--output")\n    parser.add_argument("--exhaustive", action="store_true")')
    wrapper = wrapper.replace('str(HIDDEN / "runner.py")],', 'str(HIDDEN / "runner.py")] + (["--exhaustive"] if arguments.exhaustive else []),')
    wrapper = wrapper.replace("timeout=660", "timeout=1500").replace('"wall_limit_seconds": 660, "cpu_limit_seconds": 400', '"wall_limit_seconds": 1500, "cpu_limit_seconds": 900')
    files["evaluator/evaluate.py"] = wrapper
    runner = (ROOT / "evaluator/hidden/runner.py").read_text().replace("(400, 401)", "(900, 901)")
    runner = runner.replace("result = assess(parameters)", 'result = assess(parameters, exhaustive="--exhaustive" in sys.argv[1:])')
    files["evaluator/hidden/runner.py"] = runner
    contract = (ROOT / "evaluator/test_contract.py").read_text()
    contract = contract.replace("37", "69").replace("36", "68").replace("660", "1500").replace("400", "900")
    contract = contract.replace('result["group_scores"]["corner"] == 0.0', 'result["group_scores"]["joint_preparation"] == 0.0')
    contract = contract.replace('    search_api.assess_member = original\n', '''    counts[0] = 0
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
''')
    contract = contract.replace('    parameters = search_api.parse_submission', '''    predecessor = json.loads((ROOT / "evaluator/hidden/predecessor_protocol.json").read_text())
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
    parameters = search_api.parse_submission''')
    contract = contract.replace('"public_frozen_byte_identity"', '"public_frozen_byte_identity", "all_37_predecessor_members_retained", "six_factor_parity_fixed_before_measurement", "every_five_factor_projection_complete", "unchanged_equations_admissibility_reference_thresholds", "exhaustive_failure_visits_all_69", "exhaustive_unresolved_still_fails_closed"')
    files["evaluator/test_contract.py"] = contract
    checker = (ROOT / "participant/workspace/check.py").read_text()
    checker = checker.replace('parser.add_argument("--family", action="store_true")', 'parser.add_argument("--family", action="store_true")\n    parser.add_argument("--exhaustive", action="store_true")')
    files["participant/workspace/check.py"] = checker.replace("result = assess(parameters)", "result = assess(parameters, exhaustive=arguments.exhaustive)")
    files["participant/baseline/search.py"] = (ROOT / "participant/baseline/search.py").read_text().replace("verified_generation_1_champion", "verified_generation_2_champion")
    files["participant/baseline/champion.json"] = (ROOT / "champions/generation_2/submission.json").read_text()
    files["participant/TASK.md"] = """# Robust false convergence under joint preparation uncertainty

Find admissible smooth nonlinear periodic fields for which the supplied step-halving certificate passes, yet the low-wave-number component densities disagree substantially with independently converged references at every scored late time and every public perturbation.

Generation three retains the previous uncertainty design and adds a balanced joint preparation design. The equations, admissibility bounds, numerical accuracy thresholds and physical gap target are unchanged. This challenges the supplied numerical workflow, not XMDS2 itself.

Submit one parameter JSON. The complete interface, finite uncertainty family, target, references and resource limits are in `input/protocol.json`; runnable tools are in `workspace/`. The baseline copies the strongest officially passing previous-generation champion, not a solution to this generation. Do not modify the provided method or reference.
"""
    files["participant/workspace/README.md"] = """# Local interface

Run from the generation root:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --guards --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --quick --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
```

`search_api.parse_submission`, `family`, `certificate_screen`, `screen`, `assess_member`, `reference` and `assess` are importable. `simulator.quick` provides an uncertified inexpensive screening reference, never acceptance. `assess_member` assesses one already-perturbed parameter dictionary. `assess` assesses the entire explicit protocol family.

Default full checks prioritize exact diagnostic guard failures, then fully validate a reference before any certified early rejection. A pass requires every one of the 69 members. `--exhaustive` on the checker/evaluator, or `assess(parameters, exhaustive=True)`, also visits remaining members after threshold failures. An unresolved reference still stops as invalid. Exhaustive mode does not change scoring.

The evaluator accepts data only, uses its private frozen copy, and returns one finite objective JSON with exact binary score, validity, reason, per-member uncertainty, completeness and resource information. Wall/CPU limits are 1500/900 seconds, memory 1536 MiB, one numerical thread. Development budget is 3600 CPU seconds. Python 3 with NumPy and SciPy is sufficient.
"""
    files["attempts/README.md"] = "# Pending tournament\n\nNo fresh generation-three agents have been launched. Baseline smoke and exhaustive workload outputs are generator checks, not empirical fresh attempts.\n"
    files["champions/README.md"] = "# No generation-three champion\n\nThe supplied baseline is the archived generation-two champion. No passing generation-three artifact is claimed.\n"
    files["status.json"] = serialized({"generation": 3, "maximum_generation": 3, "mode": "B", "status": "pending_tournament", "sealed": False, "fresh_agents_launched": 0, "known_generation_3_passing_witness": False, "previous_generation_solved": True, "baseline": "verified_generation_2_v_3", "note": "Staged privately; root initial/published package untouched. Resource calibration and controls precede sealing."})
    files["evaluator/hidden/ratchet_evidence.json"] = serialized({"champion": "generation_2/v_3", "selection": json.loads((ROOT / "champions/generation_2/selection.json").read_text()), "selected_factor": arguments.variable, "selected_width": arguments.width, "operation": operation, "axis_controls": controls, "fully_referenced_failures": failures, "scope": "Certified finite joint-uncertainty failure; no allegation that the previous evaluator erred, and no claim of a generation-three passing witness."})
    provenance = json.loads((ROOT / "provenance.json").read_text())
    provenance["generation_3"] = {"date": "2026-08-28", "source_native_connection": "Retains the source-native method-of-lines, interaction-picture exact linear dynamics, and step-halving error-check critique of the original challenge. No source claims or solver equations were changed.", "ratchet": "Both official generation-two attempts solved the task. The stronger archived champion fails a fully referenced joint uncertainty case while the independent new-factor axis controls pass.", "unchanged_thresholds": source_protocol["limits"], "unchanged_gap": 0.3, "audit_location": "adversary/ratchet_2", "selection": {"variable": arguments.variable, "width": arguments.width, "operation": operation}}
    files["provenance.json"] = serialized(provenance)
    files["provenance.md"] = (ROOT / "provenance.md").read_text() + "\n## Generation-three ratchet\n\nThe source-native connection is unchanged. Both generation-two fresh evaluations passed officially. V3 has the stronger minimum normalized constraint margin and supplies the baseline. Private perturbation audits select a small joint physical uncertainty with fully resolved references, not a numerical threshold increase. The final finite public family and limits are frozen before fresh trials.\n"
    files["README.md"] = """# Generation three: final staged Mode B ratchet

This is a self-contained staged package. Root published files are not modified. The previous officially passing champion is supplied as the baseline. No new fresh agent has been launched and empirical status remains `pending_tournament`.

See `participant/TASK.md`, `participant/input/protocol.json`, `evaluator/hidden/ratchet_evidence.json` and the generator resource/control records. The exact target is gap >=0.30 at all three late times for all 69 public members, certificate <=1e-4, unchanged tail/conservation/reference constraints. Default rejection is fully reference-certified; full acceptance visits all members.
"""
    snapshot = {}
    for folder in (ROOT / "participant", ROOT / "evaluator", ROOT / "attempts"):
        for path in folder.rglob("*"):
            if path.is_file() and not path.is_symlink():
                snapshot[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    snapshot["status.json"] = hashlib.sha256((ROOT / "status.json").read_bytes()).hexdigest()
    files["adversary/root_readonly_snapshot.json"] = serialized(snapshot)
    patch = ["*** Begin Patch"]
    for relative, content in files.items():
        patch.append("*** Add File: " + str(STAGE / relative))
        patch.extend("+" + line for line in content.splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(patch) + "\n", text=True, check=True)
    print(serialized({"staged": str(STAGE), "members": len(protocol["family"]), "selected_variable": arguments.variable, "width": arguments.width, "verified_failures": len(failures), "status": "unsealed_pending_resource_calibration"}))


if __name__ == "__main__":
    main()
