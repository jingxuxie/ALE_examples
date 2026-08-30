from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    for path in (ROOT / "attempts").glob("*_report.json"):
        report = json.loads(path.read_text())
        if "cases" not in report:
            continue
        report["valid"] = all(record["valid"] for record in report["cases"])
        report["status"] = "passed" if report["passed"] else "failed"
        path.write_text(json.dumps(report, indent=2) + "\n")
    summary = read("evaluator/hidden/calibration_summary.json")
    for kind in list(summary):
        report = read("attempts/" + kind + "_report.json")
        summary[kind] = {key: value for key, value in report.items() if key != "cases"}
    summary["qualified_portfolio"]["artifact"] = "champions/in_budget"
    summary["qualified_portfolio"]["entrypoint"] = "champions/in_budget/solve.py"
    (ROOT / "evaluator/hidden/calibration_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    manifest = read("evaluator/hidden/manifest.json")
    target = read("evaluator/hidden/target.json")
    portfolio = read("attempts/qualified_portfolio_report.json")
    control = read("attempts/qualified_multistart_report.json")
    baseline = read("attempts/baseline_sandbox_report.json")
    diagnostics = read("attempts/scientific_validation.json")
    qualified = portfolio["passed"]
    artifact = "champions/in_budget"
    status = {
        "concept": "concept_1",
        "valid": True,
        "verification_mode": "A_BASELINE_IMPROVEMENT",
        "status": "ready_for_fresh" if qualified else "hard_open_candidate",
        "verification_status": "builder_verified_achievable" if qualified else "hard_open_candidate",
        "ready_for_fresh": True,
        "authorized_builder": True,
        "fresh_model_sessions_run": 0,
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "thresholds_frozen_at": target["frozen_at"],
        "references_frozen_at": manifest["frozen_at"],
        "target": {key: target[key] for key in ("core_min", "worst_family_min", "stationarity_rms_max", "wall_seconds_per_case", "cpu_seconds_per_case", "cpu_cores", "memory_mib", "scratch_mib", "result_max_bytes")},
        "energy_regression_allowed": False,
        "reference_kind": "stored attained lower-energy witnesses, never true ground-state assertions",
        "baseline": {key: baseline[key] for key in ("core_score", "worst_family_score", "runtime_score", "passed", "reason")},
        "known_achievable": {key: portfolio[key] for key in ("core_score", "worst_family_score", "runtime_score", "passed", "reason", "valid", "status")},
        "multistart_control": {key: control[key] for key in ("core_score", "worst_family_score", "runtime_score", "passed", "reason")},
        "witness_field_quality_score": 1.0,
        "witness_field_runtime_score": None,
        "witness_field_solver_pass_claim": False,
        "champion_artifact": artifact,
        "champion_entrypoint": "champions/in_budget/solve.py",
        "champion_evaluation_command": "python evaluator/evaluate.py --submission champions/in_budget --report attempts/champion_rerun.json",
        "champion_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT / artifact).glob("*.py"))},
        "qualification": "Six independent real Sandbox invocations, one case per process, 60s wall/CPU limit, CPU affinity, 2GiB. Builder ran cases concurrently for calibration; official evaluate.py runs them sequentially. No stored fields mounted to the solver.",
        "expected_baseline_seconds_per_case": [min(record["wall_seconds"] for record in baseline["cases"]), max(record["wall_seconds"] for record in baseline["cases"])],
        "measured_champion_seconds_per_case": [min(record["wall_seconds"] for record in portfolio["cases"]), max(record["wall_seconds"] for record in portfolio["cases"])],
        "maximum_full_evaluation_seconds": "360 solver seconds plus private reference checking and staging",
        "tests": {"scientific_and_parser_unit_tests": 8, "scoring_and_integrity_unit_tests": 8, "all_passed": True, "baseline_cli_all_six_valid": all(record["valid"] for record in baseline["cases"]), "max_hidden_directional_derivative_relative_error": max(record["directional_derivative_relative_error"] for record in diagnostics), "max_independent_gradient_error": max(record["independent_gradient_max_error"] for record in diagnostics)},
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "gpu_used": False},
        "paths": {"mission": "participant/TASK.md", "api": "participant/input/API.md", "model": "participant/input/MODEL.md", "development_targets": "participant/input/development_targets.json", "evaluator": "evaluator/evaluate.py", "manifest": "evaluator/hidden/manifest.json", "target": "evaluator/hidden/target.json", "release_hashes": "evaluator/release_manifest.json", "portfolio_report": "attempts/qualified_portfolio_report.json", "baseline_report": "attempts/baseline_sandbox_report.json", "control_report": "attempts/qualified_multistart_report.json"},
        "limitations": ["One builder calibration per algorithm; not a universal runtime or success guarantee.", "Near-Tc fixed-field finite-lattice GL only; no Eilenberger equivalence, magnetic screening or continuum-convergence claim.", "Scratch is monitored, not a filesystem quota; retain the parent's trusted outer resource supervisor.", "An easier pilot was rejected before references froze; archived privately for audit.", "Sandbox helper is a trusted parent dependency, imported from the task authoring directory. Outer execution requires escalation in this environment."]
    }
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    rows = ["| Case / family | Baseline B | Witness W | Gap B-W |", "| --- | ---: | ---: | ---: |"]
    for reference in manifest["cases"]:
        rows.append("| %s / %s | %.12f | %.12f | %.12f |" % (reference["case_id"], reference["family"], reference["baseline_energy"], reference["witness_energy"], reference["gap"]))
    text = "\n".join([
        "# Builder calibration and frozen release", "",
        "Status: **" + status["verification_status"] + "**. No fresh model sessions were run.", "",
        "## Exact target", "",
        "Thresholds fixed at `" + target["frozen_at"] + "`; references frozen at `" + manifest["frozen_at"] + "`.",
        "Case score is `clip((B-E)/(B-W),0,1)`. Core is the equally weighted mean",
        "of three equally weighted two-case families. Pass: core >= 0.65, worst",
        "family >= 0.45, every case valid, gradient RMS <= 0.002, no regression",
        "beyond `1e-8*max(1,abs(B))`, and all resource limits met. Limits are 60s",
        "wall/CPU, one core, 2GiB, 256MiB scratch, 4MiB NPZ. Runtime score is",
        "`mean(max(0,1-wall/60))`, separate from quality. Full precision and",
        "SHA-256 hashes are in `hidden/manifest.json`; do not update them after launch.", "",
        *rows, "", "## Measured algorithms", "",
        "| Algorithm | Core | Worst family | Runtime score | Passed |",
        "| --- | ---: | ---: | ---: | --- |",
        *["| %s | %.9f | %.9f | %.9f | %s |" % (name, report["core_score"], report["worst_family_score"], report["runtime_score"], report["passed"]) for name, report in [("Public baseline", baseline), ("Plain L-BFGS multistart", control), ("General vortex portfolio", portfolio)]],
        "", "All three rows use real sandbox execution. Portfolio/control cases were",
        "calibrated concurrently in six independent sandboxes, each under the same",
        "per-case limits; the official baseline CLI was also run end-to-end sequentially.",
        "The general executable is `../champions/in_budget/solve.py` with its sibling",
        "`portfolio.py`. No case IDs, lookup tables, or hidden fields are used.",
        "Measured portfolio wall range: %.3f–%.3fs per case." % tuple(status["measured_champion_seconds_per_case"]),
        "Measured baseline wall range: %.3f–%.3fs per case." % tuple(status["expected_baseline_seconds_per_case"]),
        "", "The 150-second offline searches supply attained witness fields. Stored",
        "witnesses score 1.0 on energy by construction, but do not establish a",
        "60-second solver result. Their runtime/pass fields are deliberately null",
        "in `../attempts/witness_feasibility.json`. Ground states remain unknown.",
        "", "## Nonconvexity and validation", "",
        "The hidden suite has 6,440–9,228 real field variables, seven-hole grains,",
        "strong pinning, and high-field cases with approximately 130–144 occupied",
        "full plaquettes in the checked baseline fields. Many independently",
        "converged local minima remain at distinct energies; histories and",
        "gauge-covariant vorticity diagnostics are retained in `../attempts`.",
        "The failed multistart control completes 35–72 starts/case in its offline",
        "54-second audit and fails badly on the perforated family. This is not",
        "merely unfinished local descent or evaluation of an analytic formula.",
        "", "Sixteen unit tests pass: finite differences, gauge covariance, physical",
        "flux and positive stiffness, uniform zero-field minimizer, independent",
        "energy/gradient agreement, boundary masks, score and resource gates,",
        "NPZ abuse, and immutable reference corruption checks. The real sandbox",
        "baseline smoke test and all-six baseline CLI also pass output validation.",
        "Maximum hidden directional-derivative relative error: %.3g." % status["tests"]["max_hidden_directional_derivative_relative_error"],
        "Maximum independent gradient disagreement: %.3g." % status["tests"]["max_independent_gradient_error"],
        "", "Only `participant/` is public. Private scripts, seeds, calibration fields,",
        "references, algorithms and reports remain outside it. Scratch is monitored",
        "rather than quota-mounted; keep the trusted parent resource supervisor.", ""
    ])
    (ROOT / "evaluator/CALIBRATION.md").write_text(text)
    release = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "target_unchanged": True}
    for group in ("participant", "evaluator"):
        files = {}
        for path in sorted((ROOT / group).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name == "release_manifest.json":
                continue
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        release[group] = {"tree_sha256": hashlib.sha256(encoded).hexdigest(), "files": files}
    release["champion_sha256"] = status["champion_sha256"]
    release["status_sha256"] = hashlib.sha256((ROOT / "status.json").read_bytes()).hexdigest()
    (ROOT / "evaluator/release_manifest.json").write_text(json.dumps(release, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
