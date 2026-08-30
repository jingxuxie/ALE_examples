import copy
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGE = ROOT / "generations/generation_2"
CHAMPION = ROOT / "champions/generation_1"
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from field_control import read_json, references, summarize, validate_artifact


def text_json(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def add_files(files):
    lines = ["*** Begin Patch"]
    for path, text in files.items():
        if path.exists():
            raise RuntimeError("refusing to overwrite an existing staged asset: " + str(path))
        lines.append("*** Add File: " + str(path.relative_to(ROOT)))
        lines.extend("+" + line for line in text.splitlines())
    lines.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(lines) + "\n", text=True, cwd=ROOT, check=True)


def main():
    old_protocol = read_json(ROOT / "evaluator/hidden/protocol.json")
    protocol = copy.deepcopy(old_protocol)
    report = read_json(HERE / "certification_summary.json")
    certified = read_json(HERE / "certified_cases.json", 262144)
    failures = sorted([entry for entry in certified if entry["valid"] and entry["audited_fidelity"] < 0.98], key=lambda entry: entry["audited_fidelity"])
    if len(failures) < 16:
        raise RuntimeError("need at least sixteen certified fidelity failures; got %d" % len(failures))
    for extra in report["extra_refinement"]:
        if "strong_fidelity_failure" in extra["purpose"]:
            assert extra["fidelity"] < 0.98
            assert extra["fidelity_difference_from_frozen_C"] < 0.0001
            assert extra["state_distance_from_frozen_C"] < 0.002
    keys = list(protocol["uncertainty"])
    features = np.asarray([[(entry["case"][key] - protocol["uncertainty"][key][0]) / np.ptp(protocol["uncertainty"][key]) for key in keys] for entry in failures])
    anchors = [0]
    while len(anchors) < 4:
        distance = np.min(np.sum((features[:, None] - features[anchors][None]) ** 2, axis=2), axis=1)
        distance[anchors] = -1
        anchors.append(int(np.argmax(distance)))
    labels = np.argmin(np.sum((features[:, None] - features[anchors][None]) ** 2, axis=2), axis=1)
    public_examples = []
    regions = []
    for label, index in enumerate(anchors):
        public_examples.append(dict(failures[index]["case"], id="ratchet_example_%02d" % label, family="public"))
        members = [entry for entry, assigned in zip(failures, labels) if assigned == label]
        regions.append({"id": "joint_cluster_%02d" % label, "ranges": {key: [min(entry["case"][key] for entry in members), max(entry["case"][key] for entry in members)] for key in keys}, "public_anchor": "ratchet_example_%02d" % label, "meaning": "A diagnostic joint-extreme failure region; the complete original Cartesian uncertainty box still applies."})
    hidden_indices = [index for index in range(len(failures)) if index not in anchors][:12]
    hidden_examples = [dict(failures[index]["case"], id="focused_joint_%02d" % number, family="joint") for number, index in enumerate(hidden_indices)]
    public_cases = read_json(ROOT / "participant/input/public_cases.json") + public_examples
    legacy_cases = read_json(ROOT / "evaluator/hidden/cases.json")
    cases = legacy_cases + public_examples + hidden_examples
    protocol["protocol"] = "coherent_gp_splitter_v1_ratchet1"
    protocol["generation"] = 2
    protocol["ratchet"] = 1
    protocol["parent_protocol"] = old_protocol["protocol"]
    protocol["family_counts"] = {family: sum(case["family"] == family for case in cases) for family in old_protocol["family_counts"]}
    assert protocol["family_counts"] == {"public": 9, "interaction": 4, "calibration": 4, "trap": 4, "joint": 16}
    invariant_keys = ("duration", "coefficient_count", "spline_degree", "domain", "channels", "rf_radius", "artifact_max_bytes", "uncertainty", "nominal", "thresholds", "audit", "construction_budget")
    for key in invariant_keys:
        assert protocol[key] == old_protocol[key]
    champion_path = ROOT / "attempts/v_2/control.json"
    champion_score_path = ROOT / "attempts/v_2.evaluation.json"
    champion_score = read_json(champion_score_path)
    champion = read_json(champion_path)
    validate_artifact(champion, protocol)
    run = read_json(ROOT / "attempts/v_2.run.json")
    champion_hash = hashlib.sha256(champion_path.read_bytes()).hexdigest()
    assert run["submission_sha256"]["control.json"] == champion_hash
    assert champion_score["valid"] and champion_score["passed"]
    cutoff = datetime.datetime.fromisoformat(run["started_at"]) + datetime.timedelta(seconds=run["limit_seconds"])
    modified = datetime.datetime.fromtimestamp(champion_path.stat().st_mtime, datetime.timezone.utc)
    assert modified < cutoff
    provenance = {"generation": 1, "source": "attempts/v_2/control.json", "score_source": "attempts/v_2.evaluation.json", "sha256": champion_hash, "score_sha256": hashlib.sha256(champion_score_path.read_bytes()).hexdigest(), "cutoff_record": "attempts/v_2.run.json", "cutoff_record_pointer": "submission_sha256/control.json", "mtime_utc": modified.isoformat(), "cutoff_utc": cutoff.isoformat(), "original_before_deadline": True, "generation_1_solved": True, "post_deadline_control_modifications": 0}
    selection = {"ratchet": 1, "generation": 2, "method": "Four farthest-first public anchors among the strongest certified safe failures; twelve additional lowest-fidelity safe held-out cases; all 21 legacy cases retained.", "source_champion": provenance, "public_source_ids": [failures[index]["case"]["id"] for index in anchors], "hidden_source_ids": [failures[index]["case"]["id"] for index in hidden_indices], "clusters": [{"region": region, "members": [{"source_id": entry["case"]["id"], "audited_fidelity": entry["audited_fidelity"]} for entry, assigned in zip(failures, labels) if assigned == label]} for label, region in enumerate(regions)], "unchanged_protocol_fields": list(invariant_keys), "reference_failures_selected": 0, "numerically_invalid_cases_selected": 0, "new_generation_solvability": "unknown", "private_optimization_runs": 0, "fresh_agents_run": 0}
    (HERE / "selection.json").write_text(text_json(selection))
    task = """# Robust coherent matter-wave splitter — ratchet 1

Construct one smooth, bounded six-channel waveform that transports and coherently
splits a two-component nonlinear condensate in eight dimensionless time units.
The same waveform must work across the full public eight-parameter uncertainty
box. Complete two-dimensional complex-field fidelity matters, including relative
phase; matching densities alone is insufficient.

**Assets.** `input/SPEC.md` defines the equations, target, interface and scoring.
`input/protocol.json` contains all constants and control limits. Nine development
cases are in `input/public_cases.json`; `input/focus_regions.json` identifies
diagnostic joint-extreme regions without narrowing the uncertainty box.
`workspace/field_control.py` and `workspace/smoke.py` provide a NumPy/SciPy simulator.
`baseline/control.json` is the preceding generation's champion: physically valid,
but below this generation's fidelity requirements.

**Deliverable.** Write exactly `control.json` in the assigned writable output
directory. Submit the prescribed JSON coefficient arrays only: 25 cubic B-spline
coefficients per channel. No executable, callback, predicted field or case-specific
control is accepted. The participant package itself is read-only.

**Public diagnostic.** From the participant directory, replacing the output path:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -I -B workspace/smoke.py --artifact /path/to/output/control.json --cache-dir /path/to/output/cache
```

The command prints a diagnostic score and writes only to an explicitly supplied
cache directory. Without `--cache-dir`, references remain in memory. Optional
`--output` must point into the assigned writable output directory.

**Objective.** Pass with audited core fidelity >=0.990, worst-family mean >=0.985
and worst individual case >=0.980, satisfying all continuous-control certificates
and numerical audits. All legacy cases remain; joint-extreme coverage is stronger.
Resource efficiency breaks fidelity ties. Coarse scores cannot certify passing.

**Resources.** One hour, four CPU cores, 4 GiB RAM; Python 3, NumPy and SciPy only.
No network, GPU or XMDS2 installation is needed. The output is a designed control
artifact, not an implementation of a formula.
"""
    spec = (ROOT / "participant/input/SPEC.md").read_text()
    spec = spec.replace("# Public protocol: coherent_gp_splitter_v1", "# Public protocol: coherent_gp_splitter_v1_ratchet1")
    spec = spec.replace("## 1. Field equation and units", "This is ratchet 1, generation 2 of the same control problem, not a new concept.\nEquations, the complete uncertainty box, T=8, hardware bounds, numerical audits\nand all three passing thresholds are unchanged. All 21 original evaluation\ncases remain. Four public examples and twelve held-out joint-extreme cases add\ncoverage of independently refined, genuine fidelity failures of the prior champion.\nThe diagnostic regions in `focus_regions.json` do not restrict the original box.\n\n## 1. Field equation and units")
    spec = spec.replace("Submit UTF-8 JSON, at most 65536 bytes", "Submit `control.json` as UTF-8 JSON, at most 65536 bytes")
    spec = spec.replace("public (the five supplied cases)", "public (the nine supplied cases)")
    spec = spec.replace("and joint (four varying all\neight parameters)", "and joint (sixteen varying all\neight parameters: four legacy cases and twelve focused held-out cases)")
    spec = spec.replace("exact private coordinates are withheld", "exact private coordinates, including the focused joint cases, are withheld")
    spec = spec.replace("References are cached by parameter/grid hash and are\nindependent of the waveform.", "References are independent of the waveform. The smoke CLI defaults to in-memory\nreference construction and writes a parameter/grid cache only when `--cache-dir`\nexplicitly names a writable output directory.")
    marker = "The\nweak baseline uses"
    if marker in spec:
        spec = spec[:spec.index(marker)] + "The baseline is the preceding generation's original champion, copied without\ncoefficient changes. It passes the legacy evaluation but fails the expanded\ncoverage by fidelity, not by reference uncertainty or numerical invalidity.\n"
    else:
        marker = "The weak baseline uses"
        if marker in spec:
            spec = spec[:spec.index(marker)] + "The baseline is the unmodified preceding generation champion. It passes the\nlegacy evaluation but fails expanded coverage by numerically certified fidelity.\n"
        else:
            raise RuntimeError("baseline description anchor changed; inspect before staging")
    smoke = (ROOT / "participant/workspace/smoke.py").read_text()
    smoke = smoke.replace('    parser.add_argument("--output")', '    parser.add_argument("--output")\n    parser.add_argument("--cache-dir", help="Optional writable reference cache; default is no disk cache")')
    smoke = smoke.replace('references(cases, shape, root / "workspace/cache")', 'references(cases, shape, arguments.cache_dir)')
    validation = (ROOT / "authoring/validate.py").read_text().replace("assert len(hidden) == 21", 'assert len(hidden) == sum(protocol["family_counts"].values())')
    files = {
        CHAMPION / "control.json": champion_path.read_text(),
        CHAMPION / "evaluation.json": champion_score_path.read_text(),
        CHAMPION / "provenance.json": text_json(provenance),
        STAGE / "participant/TASK.md": task,
        STAGE / "participant/input/SPEC.md": spec,
        STAGE / "participant/input/protocol.json": text_json(protocol),
        STAGE / "participant/input/public_cases.json": text_json(public_cases),
        STAGE / "participant/input/focus_regions.json": text_json(regions),
        STAGE / "participant/input/SOURCES.md": (ROOT / "participant/input/SOURCES.md").read_text(),
        STAGE / "participant/workspace/field_control.py": (ROOT / "participant/workspace/field_control.py").read_text(),
        STAGE / "participant/workspace/smoke.py": smoke,
        STAGE / "participant/baseline/control.json": champion_path.read_text(),
        STAGE / "participant/baseline/README.md": "# Previous-generation champion\n\nThis JSON is the unmodified original generation-1 champion. Its coefficient\nvalues are not regenerated by a baseline script. `score.json` is the public\ndiagnostic; `official_summary.json` summarizes the expanded trusted evaluation.\nThe baseline is numerically valid but does not pass the expanded fidelity tests.\n",
        STAGE / "evaluator/evaluate.py": (ROOT / "evaluator/evaluate.py").read_text(),
        STAGE / "evaluator/hidden/field_control.py": (ROOT / "evaluator/hidden/field_control.py").read_text(),
        STAGE / "evaluator/hidden/protocol.json": text_json(protocol),
        STAGE / "evaluator/hidden/cases.json": text_json(cases),
        STAGE / "authoring/validate.py": validation,
        STAGE / "attempts/status.json": text_json({"status": "baseline_validation_pending", "fresh_agents_run": 0}),
        STAGE / "adversary/status.json": text_json({"status": "validation_pending", "fresh_agents_run": 0}),
        STAGE / "champions/status.json": text_json({"status": "pending_tournament", "champion": None}),
        STAGE / "status.json": text_json({"concept": "concept_3", "generation": 2, "ratchet": 1, "mode": "C", "status": "pending_tournament", "known_passing_solution": False, "solvability": "unknown", "hardness_finalized": False, "fresh_agents_run": 0, "thresholds": protocol["thresholds"]})
    }
    add_files(files)
    assert (CHAMPION / "control.json").read_bytes() == champion_path.read_bytes()
    assert (STAGE / "participant/baseline/control.json").read_bytes() == champion_path.read_bytes()
    assert (STAGE / "evaluator/evaluate.py").read_bytes() == (ROOT / "evaluator/evaluate.py").read_bytes()
    assert (STAGE / "evaluator/hidden/field_control.py").read_bytes() == (ROOT / "evaluator/hidden/field_control.py").read_bytes()
    for shape in ((80, 40), (112, 56)):
        initial, target, residual = references(cases, shape, STAGE / "evaluator/hidden/references")
        print(text_json({"prepared_shape": shape, "cases": len(cases), "maximum_reference_residual": residual}), flush=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    commands = [
        [sys.executable, "-I", "-B", str(STAGE / "participant/workspace/smoke.py"), "--artifact", str(STAGE / "participant/baseline/control.json"), "--output", str(STAGE / "participant/baseline/score.json")],
        [sys.executable, "-I", "-B", str(STAGE / "authoring/validate.py")],
        [sys.executable, "-I", "-B", str(STAGE / "evaluator/evaluate.py"), "--artifact", str(STAGE / "participant/baseline/control.json"), "--output", str(STAGE / "attempts/baseline_evaluation.json")]
    ]
    for index, command in enumerate(commands):
        process = subprocess.run(command, cwd=STAGE, env=environment, text=True, capture_output=True, timeout=700)
        (HERE / ("stage_check_%d.log" % index)).write_text(process.stdout + process.stderr)
        print(text_json({"command": command, "returncode": process.returncode}), flush=True)
        if process.returncode:
            raise RuntimeError("stage check failed; inspect stage_check_%d.log" % index)
    result = read_json(STAGE / "attempts/baseline_evaluation.json")
    assert result["valid"] and not result["passed"] and result["reason"] == "fidelity_threshold_not_met", result
    print(text_json({key: result[key] for key in ("valid", "passed", "reason", "core_score", "worst_family_score", "worst_case_score", "audits")}), flush=True)


if __name__ == "__main__":
    main()
