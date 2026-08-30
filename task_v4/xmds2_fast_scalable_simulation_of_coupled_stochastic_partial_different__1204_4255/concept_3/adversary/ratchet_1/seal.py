import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGE = ROOT / "generations/generation_2"


def read(path):
    return json.loads(path.read_text())


def render(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def snapshot(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file()}


def add_files(files):
    lines = ["*** Begin Patch"]
    for path, text in files.items():
        assert not path.exists(), path
        lines.append("*** Add File: " + str(path.relative_to(ROOT)))
        lines.extend("+" + line for line in text.splitlines())
    lines.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(lines) + "\n", text=True, cwd=ROOT, check=True)


def main():
    baseline = read(STAGE / "attempts/baseline_evaluation.json")
    validation = read(STAGE / "adversary/validation.json")
    screen = read(HERE / "broad_screen.json")
    certification = read(HERE / "certification_summary.json")
    selection = read(HERE / "selection.json")
    protocol = read(STAGE / "participant/input/protocol.json")
    parent = read(ROOT / "participant/input/protocol.json")
    assert baseline["valid"] and not baseline["passed"] and baseline["reason"] == "fidelity_threshold_not_met"
    assert validation["passed"]
    for key in selection["unchanged_protocol_fields"]:
        assert protocol[key] == parent[key]
    before = snapshot(STAGE / "participant")
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    base_command = [sys.executable, "-I", "-B", str(STAGE / "participant/workspace/smoke.py"), "--artifact", str(STAGE / "participant/baseline/control.json")]
    smoke_records = []
    for name, extra in (("no_cache", []), ("explicit_cache", ["--cache-dir", str(HERE / "public_cache")])):
        command = base_command + extra + ["--output", str(HERE / (name + ".json"))]
        process = subprocess.run(command, env=environment, cwd=HERE, capture_output=True, text=True, timeout=120)
        assert process.returncode == 0, process.stderr + process.stdout
        score = read(HERE / (name + ".json"))
        assert score["valid"]
        smoke_records.append({"mode": name, "core_score": score["core_score"], "worst_case_score": score["worst_case_score"], "command": command})
    assert abs(smoke_records[0]["core_score"] - smoke_records[1]["core_score"]) < 1e-12
    assert snapshot(STAGE / "participant") == before
    assert not (STAGE / "participant/workspace/cache").exists()
    artifact = read(STAGE / "participant/baseline/control.json")
    artifact["controls"]["center"][10] = float("nan")
    bad = HERE / "nan_control.json"
    bad.write_text(json.dumps(artifact) + "\n")
    process = subprocess.run([sys.executable, "-I", "-B", str(STAGE / "evaluator/evaluate.py"), "--artifact", str(bad)], env=environment, capture_output=True, text=True, timeout=30)
    invalid = json.loads(process.stdout)
    assert process.returncode == 2 and not invalid["valid"] and not invalid["passed"]
    assert invalid["core_score"] == 0 and invalid["worst_family_score"] == 0
    tests = {"passed": True, "participant_tree_unchanged_by_smoke": True, "default_creates_no_disk_cache": True, "explicit_writable_cache_tested": True, "cache_modes_agree_to_1e_minus_12": True, "smoke_runs": smoke_records, "malformed_nan_cli": invalid, "source_reference_and_parser_suite": "adversary/validation.json"}
    (HERE / "stage_tests.json").write_text(render(tests))
    summary_keys = ("protocol", "artifact_canonical_sha256", "core_score", "worst_family_score", "worst_case_score", "family_scores", "valid", "passed", "reason", "runtime_seconds", "runtime_score", "resource_score", "thresholds", "audits")
    summary = {key: baseline[key] for key in summary_keys}
    main_effects = sorted(screen["parameter_effects"], key=lambda key: abs(screen["parameter_effects"][key]["high"]["mean_fidelity"] - screen["parameter_effects"][key]["low"]["mean_fidelity"]), reverse=True)
    effect_table = "\n".join("| %s | %.6f | %.6f | %d / %d |" % (key, screen["parameter_effects"][key]["low"]["mean_fidelity"], screen["parameter_effects"][key]["high"]["mean_fidelity"], screen["parameter_effects"][key]["low"]["count_below_0_98"], screen["parameter_effects"][key]["high"]["count_below_0_98"]) for key in main_effects)
    boundary_table = "\n".join("| %s | %.9f | %.3g | %.3g | %.3g |" % (entry["case"]["id"], entry["fidelity"], entry["fidelity_difference_from_frozen_C"], entry["state_distance_from_frozen_C"], entry["boundary_mass"]) for entry in certification["extra_refinement"])
    provenance = f"""# Ratchet 1: verified joint-uncertainty coverage

This is generation 2 of concept_3, not a fourth concept. Generation 1 is solved:
both canonical original fresh controls pass its frozen evaluator. The selected
champion is the original `attempts/v_2/control.json`, copied byte-for-byte into
`champions/generation_1/control.json` and this stage's `participant/baseline/control.json`.
The organizer champion provenance includes its cutoff-record hash and timestamp.

## What changes and what does not

Only evaluation coverage and read-only-safe public smoke I/O change. Equations,
2D domain, T=8, target-state rule, full eight-dimensional uncertainty box, all
control amplitude/slew/acceleration/RF bounds, all numerical audit limits, and
the .990/.985/.980 thresholds remain identical. The trusted solver and evaluator
source bytes are unchanged. The score still equally weights five families.
All 21 legacy cases remain, with four new public examples and twelve focused
held-out joint cases: 37 total, family counts 9/4/4/4/16.

## Broad evidence and independent certification

The sampler was fixed before its runs: all 256 corners and 64 Latin-hypercube
interiors, seed 2026082801. A new 64x32, dt=.02 screen checked all 320 cases.
It found {screen['below_0_98']} raw-fidelity failures below .98
({screen['corner_below_0_98']} corners, {screen['interior_below_0_98']} interiors),
with minimum {screen['minimum_fidelity']:.9f}. These coarse numbers were leads,
not passing/failing proof. Original fresh stress files were consulted only as
scientific leads; no fresh-agent score was accepted as certification.

Independently regenerated stationary references and the trusted A/B/C integration
checked {certification['checked_cases']} selected cases. Of these,
{certification['certified_fidelity_failures']} were numerically certified fidelity
failures and {certification['numerical_failures']} failed a numerical guard.
No numerically invalid or reference-uncertain case was selected for the stage.
Reference residuals in this check reached at most {certification['max_reference_residual']:.3g}.

Strong failures and the largest boundary-tail leads also received a 160x80,
dt=.0025 independent grid/time refinement:

| Case | Extra-refined fidelity | Difference from C | State distance | Boundary mass |
| --- | --- | --- | --- | --- |
{boundary_table}

These extra checks separate spatial/temporal error from resolved probability
in the boundary guard. Boundary mass uses a hard region indicator, so its finite
grid quadrature can vary even when the complete complex field converges. A
boundary excursion is not counted as a fidelity failure. Such leads are retained
in the organizer evidence and excluded if they fail any prescribed audit.

## Failure clusters

Four normalized-parameter farthest-first anchors partition the strongest safe,
certified failures. The anchors become public examples; twelve additional
low-fidelity cases become held-out coverage. Diagnostic bounding ranges appear
in `participant/input/focus_regions.json`; they do not replace or narrow the
original Cartesian box. Exact membership and source-case IDs are recorded in
the organizer's `adversary/ratchet_1/selection.json`.

Across the full 256-corner screen, the following conditional means describe
associations, not a causal decomposition:

| Parameter | Low-end mean | High-end mean | Low/high counts below .98 |
| --- | --- | --- | --- |
{effect_table}

## Certified champion baseline on this stage

The original champion is **valid, but fails fidelity**, with audited core
{baseline['core_score']:.10f}, weakest-family mean {baseline['worst_family_score']:.10f}
and weakest-case fidelity {baseline['worst_case_score']:.10f}.
Maximum fidelity allowance is {baseline['audits']['max_allowance']:.3g}; maximum
stationary reference residual is {baseline['audits']['max_reference_residual']:.3g}.
The full frozen stage report is `attempts/baseline_evaluation.json`.

No new fresh agent or private optimizer was run. Generation-2 solvability is
unknown; failure of this champion is not evidence of impossibility or final
hardness. Stage assets and target/case hashes are frozen before the next trials.

## Scientific seed

The XMDS2 paper arXiv:1204.4255, original GrahamDennis/xpdeint examples and XMDS
Fourier/IP documentation remain the source connection. See the retained primary
source list in `participant/input/SOURCES.md`. This independent NumPy/SciPy GP
split solver is not claimed to be XMDS-generated code. The ratchet strengthens
coverage of the same atom-optical control artifact, not the physical model.
"""
    readme = """# concept_3 generation 2 — ratchet 1

Release only `participant/`. Keep evaluator, references, authoring, attempts,
adversary, champions, provenance and freeze records organizer-side. The original
root generation is untouched. `PROVENANCE.md` records the verified failure clusters.

Run from this generation directory:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/usr/bin/python3 -I -B participant/workspace/smoke.py --artifact participant/baseline/control.json
/usr/bin/python3 -I -B evaluator/evaluate.py --artifact participant/baseline/control.json --output attempts/baseline_evaluation.json
/usr/bin/python3 -I -B authoring/validate.py
```

For fresh trials, require the exact artifact filename `control.json` in the
assigned output directory. The smoke command writes no cache by default;
`--cache-dir` and `--output`, when provided, must name writable output locations.
The trusted scorer reads JSON only and uses included, organizer-generated
reference caches. Run it with isolated Python imports and read-only trusted files.
Exit 0 means valid, not passed; inspect both JSON booleans.

This stage is frozen and ready for the main worker to archive/promote and trial.
No fresh agent is launched here, and no generation-2 passing solution is known.
"""
    add_files({STAGE / "participant/baseline/official_summary.json": render(summary), STAGE / "PROVENANCE.md": provenance, STAGE / "README.md": readme, HERE / "README.md": "# Organizer-only ratchet evidence\n\n`screen_input_freeze.json` fixes the 320-case sampler before screening.\n`broad_screen.json`, `certified_cases.json` and `certification_summary.json`\nseparate coarse leads from refined failures and boundary diagnostics.\n`selection.json` explains clustering and the 37-case staged coverage.\n`stage_tests.json` verifies no-cache/default and explicit-cache smoke behavior.\nThe unmodified champion and original score live in `champions/generation_1/`.\nStage sources and baselines are in `generations/generation_2/`.\nNo root package, original attempt, or root status file is modified.\n"})
    status = read(STAGE / "status.json")
    status.update({"ready": True, "baseline_valid": True, "baseline_passed": False, "baseline_core_score": baseline["core_score"], "baseline_worst_family_score": baseline["worst_family_score"], "baseline_worst_case_score": baseline["worst_case_score"], "parent_generation_solved": True})
    (STAGE / "status.json").write_text(render(status))
    (STAGE / "attempts/status.json").write_text(render({"status": "baseline_validated_pending_tournament", "fresh_agents_run": 0, "valid": True, "passed": False, "reason": baseline["reason"]}))
    (STAGE / "adversary/status.json").write_text(render({"status": "parser_solver_refinement_and_io_tests_passed", "fresh_agents_run": 0, "hardness_finalized": False}))
    (ROOT / "champions/generation_1/status.json").write_text(render({"status": "original_champion_preserved", "source": "attempts/v_2/control.json", "valid": True, "passed": True, "generation_1_solved": True}))
    hashes = {}
    for directory in (STAGE / "participant", STAGE / "evaluator"):
        hashes.update({str((directory / relative).relative_to(STAGE)): digest for relative, digest in snapshot(directory).items()})
    hashes["attempts/baseline_evaluation.json"] = hashlib.sha256((STAGE / "attempts/baseline_evaluation.json").read_bytes()).hexdigest()
    manifest = {"concept": "concept_3", "generation": 2, "ratchet": 1, "date": "2026-08-28", "status": "pending_tournament", "ready": True, "thresholds": protocol["thresholds"], "family_counts": protocol["family_counts"], "cases": 37, "equations_and_envelope_unchanged": True, "numerical_audits_unchanged": True, "parent_solver_sha256": hashlib.sha256((ROOT / "evaluator/hidden/field_control.py").read_bytes()).hexdigest(), "fresh_agents_run": 0, "new_solvability": "unknown", "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "sha256": hashes}
    (STAGE / "freeze_manifest.json").write_text(render(manifest))
    (HERE / "ready.json").write_text(render({"ready": True, "stage": "generations/generation_2", "champion": "champions/generation_1/control.json", "baseline": summary, "broad_cases": 320, "coarse_fidelity_failures": screen["below_0_98"], "independently_checked_cases": certification["checked_cases"], "certified_fidelity_failures": certification["certified_fidelity_failures"], "fresh_agents_run": 0, "new_solvability": "unknown"}))
    print(render({"READY": True, "baseline": summary, "broad_count": 320, "broad_below_0_98": screen["below_0_98"], "certified_failures": certification["certified_fidelity_failures"], "tests_passed": True}), flush=True)


if __name__ == "__main__":
    main()
