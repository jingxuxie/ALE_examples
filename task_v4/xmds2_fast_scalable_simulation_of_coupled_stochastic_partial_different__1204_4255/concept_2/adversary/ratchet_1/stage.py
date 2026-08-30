import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "generations" / "generation_2"


def install(files):
    sections = ["*** Begin Patch"]
    for path, content in files.items():
        sections.append("*** Add File: " + str(path.relative_to(ROOT)))
        sections.extend("+" + line for line in content.splitlines())
    sections.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(sections) + "\n", text=True, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=float, required=True)
    arguments = parser.parse_args()
    assert arguments.radius in (0.01, 0.02, 0.03)
    protocol = json.loads((ROOT / "participant/input/protocol.json").read_text())
    protocol["protocol_id"] = "nonlinear_joint_uncertainty_v2"
    protocol["generation"] = 2
    protocol["family"] = [dict(member, group="legacy") for member in protocol["family"]]
    interior = json.loads((ROOT / "adversary/ratchet_1/interior_coordinates.json").read_text())
    coordinates = [("corner", index, list(point)) for index, point in enumerate(itertools.product((-1, 1), repeat=5))]
    coordinates += [("interior", index, point) for index, point in enumerate(interior)]
    for group, index, point in coordinates:
        protocol["family"].append({
            "name": group + "_" + str(index).zfill(2), "group": group,
            "coordinates": point,
            "multiply": {"nonlinearity": 1 + arguments.radius * point[0], "duration": 1 + arguments.radius * point[1]},
            "add": {"a1": 0.01 * point[2], "a2": 0.01 * point[3], "relative_phase": 0.03 * point[4]},
        })
    protocol["uncertainty_design"] = {
        "coordinates": ["nonlinearity_calibration", "duration_calibration", "first_shape", "second_shape", "relative_phase"],
        "calibration_relative_half_width": arguments.radius,
        "shape_absolute_half_width": 0.01, "phase_absolute_half_width_radians": 0.03,
        "construction": "Keep all five generation-1 members; add the complete 2^5 Cartesian corner set and 16 fixed interior points. Every member and numerical coordinate is explicitly listed in family. The two calibration signs, two shape signs, and phase sign are independent.",
        "interior_provenance": "First 16 vectors from numpy.random.default_rng(282608).uniform(-0.85,0.85,size=(16,5)); listed coordinates, not RNG regeneration, are authoritative. Generated before screening and not selected for severity.",
        "claim_scope": "Acceptance certifies the listed finite perturbation design, not every point of the continuous uncertainty box. No undisclosed or stochastic evaluation members.",
    }
    protocol["target"]["core_score"] = "Minimum of all 53 family_scores. Same value is worst_family_score. Invalid/unresolved/resource-failed runs score 0. Scores are finite and in [0,1]."
    protocol["target"]["definition"] = "For all 53 explicitly listed family members, minimum observable gap over t/T=0.75,0.875,1 minus that member's observable uncertainty, floored at zero, must be >=0.3. All four unchanged certificate/diagnostic limits must also hold for every member."
    protocol["resources"].update(evaluation_wall_seconds=420, evaluation_cpu_seconds=400)
    protocol["reference"]["evaluation_pruning"] = "The full unchanged four-solve reference check is performed for each evaluated member. On the first unresolved reference, assessment stops with valid=false, passed=false, zero score and complete_assessment=false; unresolved members cannot help a witness. Otherwise all 53 members are fully evaluated, including any guard-failing member."
    protocol["interface"]["guard_check"] = "/usr/bin/python3 participant/workspace/check.py attempts/baseline.json --guards --family"
    protocol["interface"]["baseline"] = "/usr/bin/python3 participant/baseline/search.py --output attempts/baseline.json"
    protocol["interface"]["baseline_description"] = "Copies the officially verified generation-1 v_1 champion, byte-for-byte. This previous champion is not a generation-2 solution. No private optimized witness is supplied."
    files = {}
    for directory in ("participant", "evaluator"):
        for source in (ROOT / directory).rglob("*"):
            if source.is_file() and source.suffix in (".py", ".md", ".json") and source.name != "freeze_manifest.json":
                files[OUTPUT / source.relative_to(ROOT)] = source.read_text()
    encoded_protocol = json.dumps(protocol, indent=2) + "\n"
    files[OUTPUT / "participant/input/protocol.json"] = encoded_protocol
    files[OUTPUT / "evaluator/hidden/protocol.json"] = encoded_protocol
    evaluator = files[OUTPUT / "evaluator/evaluate.py"].replace("timeout=110", "timeout=420")
    evaluator = evaluator.replace('"wall_limit_seconds": 110, "cpu_limit_seconds": 100', '"wall_limit_seconds": 420, "cpu_limit_seconds": 400')
    files[OUTPUT / "evaluator/evaluate.py"] = evaluator
    files[OUTPUT / "evaluator/hidden/runner.py"] = files[OUTPUT / "evaluator/hidden/runner.py"].replace("(100, 101)", "(400, 401)")
    api = files[OUTPUT / "participant/workspace/search_api.py"]
    api = api.replace('        reports.append({"name": name, **assess_member(member)})', '        descriptor = next(item for item in PROTOCOL["family"] if item["name"] == name)\n        reports.append({"name": name, "group": descriptor["group"], **assess_member(member)})\n        if not reports[-1]["reference"]["resolved"]:\n            break')
    api = api.replace('    passed = valid and all(report["passed"] for report in reports)', '    complete = len(reports) == len(PROTOCOL["family"])\n    passed = valid and complete and all(report["passed"] for report in reports)')
    api = api.replace('        "reason": reason, "family": reports,', '        "reason": reason, "family": reports,\n        "complete_assessment": complete, "expected_family_members": len(PROTOCOL["family"]),\n        "evaluated_family_members": len(reports),\n        "group_scores": {group: min(report["family_score"] for report in reports if report["group"] == group) for group in sorted({report["group"] for report in reports})},')
    api += '\n\ndef certificate_screen(parameters, all_members=False):\n    members = family(parameters) if all_members else [("nominal", parameters)]\n    result = {}\n    settings = PROTOCOL["method_under_test"]\n    for name, member in members:\n        coarse = integrate(member, settings["grid"], settings["coarse_steps"])\n        fine = integrate(member, settings["grid"], settings["fine_steps"])\n        coarse_diagnostics = diagnostics(member, coarse)\n        fine_diagnostics = diagnostics(member, fine)\n        metrics = {\n            "certificate": float(np.max(field_distance(coarse, fine))),\n            "tail_mass": fine_diagnostics["tail_mass"],\n            "mass_drift": max(coarse_diagnostics["mass_drift"], fine_diagnostics["mass_drift"]),\n            "energy_drift": max(coarse_diagnostics["energy_drift"], fine_diagnostics["energy_drift"]),\n        }\n        result[name] = {**metrics, "guard_passed": all(metrics[key] <= limit for key, limit in PROTOCOL["limits"].items())}\n    return result\n'
    files[OUTPUT / "participant/workspace/search_api.py"] = api
    files[OUTPUT / "evaluator/hidden/search_api.py"] = api
    checker = files[OUTPUT / "participant/workspace/check.py"].replace("assess, parse_submission, screen", "assess, certificate_screen, parse_submission, screen")
    checker = checker.replace('    parser.add_argument("--quick", action="store_true")', '    modes = parser.add_mutually_exclusive_group()\n    modes.add_argument("--quick", action="store_true")\n    modes.add_argument("--guards", action="store_true")')
    checker = checker.replace('        result = {"screening_only": True, "family": screen(parameters, arguments.family)} if arguments.quick else assess(parameters)', '        if arguments.guards:\n            result = {"screening_only": True, "guards_only": True, "family": certificate_screen(parameters, arguments.family)}\n        elif arguments.quick:\n            result = {"screening_only": True, "family": screen(parameters, arguments.family)}\n        else:\n            result = assess(parameters)')
    files[OUTPUT / "participant/workspace/check.py"] = checker
    files[OUTPUT / "participant/TASK.md"] = '# Robust false convergence under joint uncertainty\n\nFind a counterexample experiment for the supplied nonlinear periodic-field workflow that survives **independently combined calibration, initial-shape, and phase perturbations**. The previous champion is supplied as the baseline, not as a passing solution. Submit only one admissible JSON experiment; do not replace the integrator.\n\nThe complete model, public finite perturbation design, numerical-reference checks, unchanged accuracy/diagnostic thresholds, scoring, schema, and resource budget are in `input/protocol.json`. Runnable simulation and screening APIs are in `workspace/`; `baseline/search.py` copies the previous champion. Every listed family member must satisfy the target.\n\nThis falsifies a claim about the supplied workflow, not a bug claim about XMDS2. Numerical uncertainty is estimated by refinement and an independent method, not treated as a rigorous PDE bound.\n'
    champion = ROOT / "champions/generation_1/submission.json"
    files[OUTPUT / "participant/baseline/champion.json"] = champion.read_text()
    files[OUTPUT / "participant/baseline/search.py"] = 'import argparse\nimport hashlib\nimport json\nimport time\nfrom pathlib import Path\n\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument("--output", required=True)\n    arguments = parser.parse_args()\n    started = time.monotonic()\n    content = Path(__file__).with_name("champion.json").read_bytes()\n    destination = Path(arguments.output)\n    destination.parent.mkdir(parents=True, exist_ok=True)\n    destination.write_bytes(content)\n    print(json.dumps({"submission": str(destination), "source": "verified_generation_1_champion", "sha256": hashlib.sha256(content).hexdigest(), "runtime_seconds": time.monotonic() - started}))\n\n\nif __name__ == "__main__":\n    main()\n'
    files[OUTPUT / "participant/workspace/README.md"] = '# Local interface\n\nFrom the generation root:\n\n```\n/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json\n/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --guards --family\n/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --quick --family\n/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json\n/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json\n```\n\nIn a participant-only checkout, select a writable output location instead of `attempts/`; the first four commands require no evaluator files. The baseline copies the previous champion.\n\n`search_api.parse_submission(text)` validates the input. `family(parameters)` enumerates the 53 public members. `certificate_screen(parameters, all_members=False)` evaluates only the fixed-lattice temporal certificate and diagnostics, without a high-resolution reference. `screen(parameters, all_members=False)` adds an inexpensive **uncertified** density-gap estimate. `assess_member(parameters)` performs all full numerical-reference checks for one already-perturbed experiment; `assess(parameters)` performs the complete assessment. A single unresolved reference terminates a full assessment with zero credit; no unresolved or unassessed member can pass.\n\n`simulator.integrate(parameters, size, steps)` returns eight Fourier-field snapshots. `independent(parameters, size)` returns DOP853 snapshots and RHS count. Use `/usr/bin/python3` with NumPy/SciPy, single-threaded BLAS. The CLI wrappers set thread counts. No network, compiler, data download, or XMDS installation is required. The one-hour development budget and 420-second evaluator budget are separate.\n'
    files[OUTPUT / "adversary/test_controls.py"] = (ROOT / "adversary/test_controls.py").read_text()
    files[OUTPUT / "attempts/README.md"] = '# Staged generation-2 checks\n\nThese are privileged smoke tests, not fresh-agent tournament attempts.\n'
    files[OUTPUT / "champions/README.md"] = '# Generation-2 champions\n\nNo generation-2 champion is declared.\n'
    files[OUTPUT / "status.json"] = json.dumps({"generation": 2, "status": "pending_tournament", "build_status": "validation_pending", "fresh_agent_runs": 0, "baseline": "verified generation-1 v_1 champion", "baseline_submission_sha256": hashlib.sha256(champion.read_bytes()).hexdigest(), "family_members": 53, "calibration_half_width": arguments.radius, "unchanged_gap_target": 0.3, "unchanged_certificate_limit": 0.0001, "evaluation_wall_seconds": 420, "evaluation_cpu_seconds": 400, "solvability": "not yet established; no private optimized generation-2 solution supplied", "publication": "staged only; main worker handles archive, review, promotion and trials"}, indent=2) + "\n"
    files[OUTPUT / "README.md"] = '# Generation 2 staging package\n\nSelf-contained, not yet promoted. Expose only `participant/` to future tested agents. Status remains `pending_tournament`; no fresh agent has been launched for this generation.\n\nThe baseline is the verified generation-1 champion. The model, parameter ranges, three-time density-gap target 0.30, certificate limit 1e-4, diagnostic limits and four-solve reference validation are unchanged. The public family now combines the original five members with all 32 corners of an independent five-dimensional calibration/shape/phase box and 16 predetermined interior points. This is a finite-design robustness challenge, not a continuous-box proof.\n\nRun the commands in `participant/workspace/README.md`. Evaluation uses a 420-second wall / 400-second CPU budget, one thread and 1536 MiB address space. `adversary/test_controls.py` runs schema, file-type, numerical-order and frozen-copy checks after the baseline has been copied to `attempts/baseline.json`.\n\nMain must review the frozen manifest and privileged evidence before promotion. No root initial-generation files are modified by this staging package.\n'
    install(files)
    print(json.dumps({"staged_files": len(files), "radius": arguments.radius, "family_members": len(protocol["family"])}))


if __name__ == "__main__":
    main()
